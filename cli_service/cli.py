import requests
from pathlib import Path
import os
import redis
import time

IMAGE_SERVICE_URL = "http://image_service:8001"
JWT_USERNAME = os.getenv("JWT_USERNAME", "user")
JWT_PASSWORD = os.getenv("JWT_PASSWORD", "password")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_CHANNEL = "photo_channel"

jwt_token = None


def get_jwt_token():
    """Pobiera JWT token z serwisu"""
    global jwt_token

    try:
        response = requests.post(
            f"{IMAGE_SERVICE_URL}/auth/login",
            data={"username": JWT_USERNAME, "password": JWT_PASSWORD},
            timeout=10
        )
        response.raise_for_status()
        jwt_token = response.json()["access_token"]
        print("[DEBUG] Otrzymano JWT token")
        return jwt_token
    except Exception as e:
        print(f"[ERROR] Nie udało się uzyskać JWT tokena: {str(e)}")
        return None


def send_to_service(file_path, action, size=None):
    """Wysyła obraz do serwisu przetwarzającego"""
    global jwt_token

    try:
        if not jwt_token:
            jwt_token = get_jwt_token()
            if not jwt_token:
                return None

        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {"action": action}
            if size:
                data["size"] = size

            headers = {"Authorization": f"Bearer {jwt_token}"}

            r = requests.post(
                f"{IMAGE_SERVICE_URL}/process",
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )

            if r.status_code == 401:
                print("[DEBUG] Token wygasł, pobieranie nowego...")
                jwt_token = get_jwt_token()
                return send_to_service(file_path, action, size)

            r.raise_for_status()
            return r.content
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Błąd podczas wysyłania na serwer: {e}")
        return None


def wait_for_redis_message(timeout=60):
    """Czeka na wiadomość z Redis"""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        pubsub = r.pubsub()
        pubsub.subscribe(REDIS_CHANNEL)
        print("[DEBUG] Oczekiwanie na wiadomość o gotowości zdjęcia...")

        start = time.time()
        for message in pubsub.listen():
            if message['type'] == 'message':
                print(f"[DEBUG] Otrzymano wiadomość: {message['data'].decode()}")
                break
            if time.time() - start > timeout:
                print("[DEBUG] Timeout: wiadomość nie przyszła")
                break
    except Exception as e:
        print(f"[DEBUG] Błąd przy połączeniu z Redis: {e}")


def main():
    print("Klient CLI do obróbki zdjęć przez DALL-E")

    action = ""
    while action not in ["enhance", "expand"]:
        action = input("Wprowadź akcję (enhance/expand): ").strip().lower()

    size = None
    if action == "expand":
        sizes = {"1": "256x256", "2": "512x512", "3": "1024x1024"}
        print("Wybierz rozmiar:")
        print("1. 256x256\n2. 512x512\n3. 1024x1024")
        choice = ""
        while choice not in sizes:
            choice = input("Twój wybór (1/2/3): ").strip()
        size = sizes[choice]

    file_path = input("Wprowadź ścieżkę do zdjęcia: ").strip()
    if not Path(file_path).is_file():
        print("Plik nie znaleziony!")
        return

    print("Zdjęcie jest przetwarzane, czekaj...")
    image_bytes = send_to_service(file_path, action, size)
    if image_bytes is None:
        return

    wait_for_redis_message(timeout=60)

    out_file = f"result_{Path(file_path).name}"
    with open(out_file, "wb") as f:
        f.write(image_bytes)

    print(f"Gotowe! Wynik zapisany w {out_file}")


if __name__ == "__main__":
    main()
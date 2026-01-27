import requests
from pathlib import Path
import os
import redis

IMAGE_SERVICE_URL = "http://image_service:8001/process"
API_KEY = os.getenv("API_KEY", "supersecretkey")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


def send_to_service(file_path, action, size=None):
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"action": action}
        if size:
            data["size"] = size
        headers = {"x-api-key": API_KEY}
        r = requests.post(IMAGE_SERVICE_URL, files=files, data=data, headers=headers)
        r.raise_for_status()
        return r.content


def wait_for_redis_message():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    pubsub = r.pubsub()
    pubsub.subscribe("photo_channel")
    print("Чекаємо повідомлень про готовність фото...")
    for message in pubsub.listen():
        if message['type'] == 'message':
            print("Отримано повідомлення:", message['data'].decode())
            break


def main():
    print("CLI-клієнт для обробки фото через DALL·E")
    action = ""
    while action not in ["enhance", "expand"]:
        action = input("Введіть дію (enhance/expand): ").strip().lower()

    size = None
    if action == "expand":
        sizes = {"1": 1024, "2": 1920, "3": 2048}
        print("Виберіть розмір:")
        print("1. 1024x1024\n2. 1920x1080\n3. 2048x1024")
        choice = ""
        while choice not in sizes:
            choice = input("Ваш вибір (1/2/3): ").strip()
        size = sizes[choice]

    file_path = input("Введіть шлях до фото: ").strip()
    if not Path(file_path).is_file():
        print("Файл не знайдено!")
        return

    print("Фото обробляється, зачекайте...")
    image_bytes = send_to_service(file_path, action, size)

    wait_for_redis_message()

    out_file = f"result_{Path(file_path).name}"
    with open(out_file, "wb") as f:
        f.write(image_bytes)
    print(f"Готово ✅ Результат збережено у {out_file}")


if __name__ == "__main__":
    main()
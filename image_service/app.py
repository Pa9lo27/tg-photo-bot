import redis
import os
from fastapi import FastAPI, UploadFile, Form, HTTPException, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image
from openai import OpenAI
import base64
import jwt
from datetime import datetime, timedelta
import json
from typing import Set

app = FastAPI()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-zmien-w-produkcji")
ALGORITHM = "HS256"

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY nie jest ustawiony!")

client = OpenAI(api_key=api_key)

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379))
)

VALID_SIZES = ["256x256", "512x512", "1024x1024"]
connected_clients: Set[WebSocket] = set()


def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Brak tokena autentykacji")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Nieprawidłowy schemat autentykacji")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ValueError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy format tokena")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token wygasł")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy token")


async def broadcast_to_clients(message: dict):
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception as e:
            print(f"[DEBUG] Błąd wysyłania do klienta: {str(e)}")
            disconnected.add(client)

    for client in disconnected:
        connected_clients.discard(client)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"[DEBUG] Klient WebSocket podłączony. Razem: {len(connected_clients)}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[DEBUG] Wiadomość z WebSocket: {data}")
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        print(f"[DEBUG] Klient WebSocket rozłączony. Razem: {len(connected_clients)}")
    except Exception as e:
        print(f"[ERROR] Błąd WebSocket: {str(e)}")
        connected_clients.discard(websocket)


@app.post("/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username != "user" or password != "password":
        raise HTTPException(status_code=401, detail="Nieprawidłowe dane logowania")

    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    print(f"[DEBUG] Token wydany dla użytkownika: {username}")
    return {"access_token": token, "token_type": "bearer"}


@app.post("/process")
async def process_image(
        file: UploadFile,
        action: str = Form(...),
        size: str = Form(None),
        authorization: str = Header(None)
):
    verify_token(authorization)

    print(f"[DEBUG] Otrzymano żądanie: action={action}, size={size}, filename={file.filename}")

    if size and size not in VALID_SIZES:
        raise HTTPException(status_code=400, detail=f"Nieobsługiwany rozmiar. Dozwolone: {VALID_SIZES}")

    try:
        image = Image.open(file.file).convert("RGBA")
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        buffered.seek(0)
        print(f"[DEBUG] Obraz konwertowany na PNG (RGBA), rozmiar: {buffered.getbuffer().nbytes} bajtów")
    except Exception as e:
        print(f"[ERROR] Błąd podczas przetwarzania obrazu: {str(e)}")
        raise HTTPException(status_code=400, detail="Nieprawidłowy plik graficzny") from e

    prompt = "Remove pixelation and noise from the image, smooth edges, preserve natural details, realistic output, no artificial sharpening or added textures."

    if action == "expand" and size:
        prompt += f" Resize to {size}."
        api_size = size
    else:
        api_size = "1024x1024"

    print(f"[DEBUG] Prompt: {prompt}")
    print(f"[DEBUG] Rozmiar API: {api_size}")

    try:
        print("[DEBUG] Wysyłam żądanie do OpenAI API...")
        response = client.images.edit(
            image=(file.filename or "image.png", buffered, "image/png"),
            prompt=prompt,
            size=api_size,
            response_format="b64_json"
        )
        print(f"[DEBUG] Otrzymana odpowiedź od OpenAI")

    except Exception as e:
        print(f"[ERROR] OpenAI Error: {type(e).__name__}: {str(e)}")
        await broadcast_to_clients({
            "type": "error",
            "message": f"Błąd OpenAI: {str(e)}"
        })
        raise HTTPException(status_code=500, detail=f"Błąd OpenAI: {str(e)}")

    try:
        print("[DEBUG] Dekodowanie obrazu...")

        if hasattr(response, 'data') and len(response.data) > 0:
            img_response = response.data[0]

            if hasattr(img_response, 'b64_json') and img_response.b64_json:
                b64_str = img_response.b64_json
                img_data = base64.b64decode(b64_str)
                result_image = BytesIO(img_data)
                result_image.seek(0)
                print(f"[DEBUG] Obraz zdekodowany pomyślnie, rozmiar: {len(img_data)} bajtów")
            else:
                print(f"[ERROR] b64_json nie znaleziony lub pusty")
                raise AttributeError("b64_json not found or empty in response")
        else:
            print(f"[ERROR] response.data jest pusty")
            raise AttributeError("response.data is empty")

    except Exception as e:
        print(f"[ERROR] Błąd podczas dekodowania obrazu: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd dekodowania obrazu: {str(e)}") from e

    try:
        message = f"Zdjęcie gotowe dla action={action}"
        r.publish("photo_channel", message)

        await broadcast_to_clients({
            "type": "success",
            "message": message,
            "action": action
        })
        print("[DEBUG] Wiadomość wysłana do Redis i WebSocket")
    except Exception as e:
        print(f"[WARNING] Błąd Redis: {str(e)}")

    return StreamingResponse(result_image, media_type="image/png")


@app.get("/health")
async def health():
    return {"status": "OK", "connected_clients": len(connected_clients)}


@app.get("/stats")
async def stats(authorization: str = Header(None)):
    verify_token(authorization)
    return {
        "connected_websocket_clients": len(connected_clients),
        "redis_status": "connected" if r.ping() else "disconnected"
    }
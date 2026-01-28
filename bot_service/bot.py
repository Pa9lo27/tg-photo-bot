import os
import time
import asyncio
import threading
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
import requests
from io import BytesIO
import websockets
import json

IMAGE_SERVICE_URL = "http://image_service:8001"
IMAGE_SERVICE_WS = "ws://image_service:8001/ws"
JWT_USERNAME = os.getenv("JWT_USERNAME", "user")
JWT_PASSWORD = os.getenv("JWT_PASSWORD", "password")
MAX_RETRIES = 3
RETRY_DELAY = 2

VALID_SIZES = ["256x256", "512x512", "1024x1024"]

jwt_token = None
ws_connection = None
notification_queue = {}


def get_jwt_token():
    global jwt_token

    try:
        response = requests.post(
            f"{IMAGE_SERVICE_URL}/auth/login",
            data={"username": JWT_USERNAME, "password": JWT_PASSWORD},
            timeout=10
        )
        response.raise_for_status()
        jwt_token = response.json()["access_token"]
        print(f"[DEBUG] Otrzymano JWT token")
        return jwt_token
    except Exception as e:
        print(f"[ERROR] Nie udało się uzyskać JWT tokena: {str(e)}")
        return None


def send_to_image_service(file_path, action, size=None):
    global jwt_token

    for attempt in range(MAX_RETRIES):
        try:
            if not jwt_token:
                jwt_token = get_jwt_token()
                if not jwt_token:
                    raise Exception("Brak JWT tokena")

            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {"action": action}
                if size:
                    data["size"] = size

                headers = {"Authorization": f"Bearer {jwt_token}"}

                print(f"[DEBUG] Próba {attempt + 1}/{MAX_RETRIES} wysłania żądania do serwisu")
                r = requests.post(
                    f"{IMAGE_SERVICE_URL}/process",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60
                )

                if r.status_code == 401:
                    print(f"[DEBUG] Token wygasł, pobieranie nowego...")
                    jwt_token = get_jwt_token()
                    continue

                r.raise_for_status()
                print(f"[DEBUG] Pomyślnie otrzymana odpowiedź z serwisu")
                return r.content

        except requests.exceptions.ConnectionError as e:
            print(f"[DEBUG] Błąd połączenia (próba {attempt + 1}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise

        except requests.exceptions.Timeout as e:
            print(f"[DEBUG] Timeout (próba {attempt + 1}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise

        except Exception as e:
            print(f"[ERROR] Błąd: {type(e).__name__}: {str(e)}")
            raise

    raise Exception("Nie udało się wysłać żądania po wszystkich próbach")


def cleanup_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[DEBUG] Usunięto plik: {file_path}")
    except Exception as e:
        print(f"[DEBUG] Błąd przy usuwaniu pliku {file_path}: {str(e)}")


async def websocket_listener():
    global ws_connection

    while True:
        try:
            print("[DEBUG] Łączę się z WebSocket...")
            async with websockets.connect(IMAGE_SERVICE_WS) as websocket:
                ws_connection = websocket
                print("[DEBUG] Połączono z WebSocket")

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        print(f"[DEBUG] Otrzymano wiadomość WebSocket: {data}")

                        if data.get("type") == "success":
                            notification_queue["last_message"] = data
                    except json.JSONDecodeError:
                        print(f"[DEBUG] Błąd parsing JSON: {message}")
        except Exception as e:
            print(f"[ERROR] Błąd WebSocket: {str(e)}")
            ws_connection = None
            await asyncio.sleep(5)


def start_websocket_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(websocket_listener())


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN nie jest ustawiony!")

user_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Rozszerz i ulepsz", callback_data="expand")],
        [InlineKeyboardButton("Tylko ulepsz", callback_data="enhance")]
    ]
    await update.message.reply_text(
        "Wybierz akcje:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data

    user_data[user_id] = {"action": action, "photo": None}
    await query.edit_message_text("Wyslij zdjecie do obrobki:")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_data:
        await update.message.reply_text("Najpierw wybierz akcje przez /start")
        return

    try:
        photo_file = await update.message.photo[-1].get_file()
        file_path = f"temp_{user_id}.png"
        await photo_file.download_to_drive(file_path)
        user_data[user_id]["photo"] = file_path

        print(f"[DEBUG] Plik zdjęcia zapisany: {file_path}")

        action = user_data[user_id]["action"]
        if action == "expand":
            keyboard = [
                [InlineKeyboardButton(size, callback_data=f"size_{size}")]
                for size in VALID_SIZES
            ]
            await update.message.reply_text(
                "Wybierz rozmiar:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text("Zdjecie jest przetwarzane, czekaj...")
            try:
                image_bytes = send_to_image_service(file_path, action="enhance")
                await update.message.reply_photo(
                    photo=BytesIO(image_bytes),
                    caption="Gotowe"
                )
            except Exception as e:
                await update.message.reply_text(f"Błąd przy przetwarzaniu: {str(e)}")
            finally:
                cleanup_file(file_path)

    except Exception as e:
        print(f"[ERROR] Błąd w handle_photo: {type(e).__name__}: {str(e)}")
        await update.message.reply_text(f"Błąd: {str(e)}")


async def size_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        if user_id not in user_data or not user_data[user_id]["photo"]:
            await query.edit_message_text("Błąd: brak zdjęcia")
            return

        file_path = user_data[user_id]["photo"]
        size = query.data.split("_")[1]

        await query.edit_message_text("Zdjecie jest przetwarzane, czekaj...")

        image_bytes = send_to_image_service(file_path, action="expand", size=size)

        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=BytesIO(image_bytes),
            caption="Gotowe"
        )

    except requests.exceptions.ConnectionError as e:
        await query.edit_message_text(
            f"Błąd połączenia z serwisem.\nSpróbuj ponownie za chwilę."
        )
    except requests.exceptions.Timeout as e:
        await query.edit_message_text(
            "Przetwarzanie obrazu trwa zbyt długo.\nSpróbuj z mniejszym rozmiarem."
        )
    except Exception as e:
        print(f"[ERROR] Błąd w size_choice: {type(e).__name__}: {str(e)}")
        await query.edit_message_text(f"Błąd: {str(e)}")

    finally:
        if user_id in user_data and user_data[user_id]["photo"]:
            cleanup_file(user_data[user_id]["photo"])
            user_data[user_id]["photo"] = None


if __name__ == "__main__":
    jwt_token = get_jwt_token()

    ws_thread = threading.Thread(target=start_websocket_listener, daemon=True)
    ws_thread.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="^(expand|enhance)$"))
    app.add_handler(CallbackQueryHandler(size_choice, pattern="^size_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("[DEBUG] Uruchomienie bota...")
    app.run_polling()
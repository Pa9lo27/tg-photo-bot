import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
import requests
from io import BytesIO

IMAGE_SERVICE_URL = "http://image_service:8001/process"

def send_to_image_service(file_path, action, size=None):
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"action": action}
        if size:
            data["size"] = size

        r = requests.post(IMAGE_SERVICE_URL, files=files, data=data)
        r.raise_for_status()
        return r.content

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Розширити + покращити", callback_data="expand")],
        [InlineKeyboardButton("Просто покращити", callback_data="enhance")]
    ]
    await update.message.reply_text("Виберіть дію:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data

    user_data[user_id] = {"action": action, "photo": None}
    await query.edit_message_text("Надішліть фото для обробки:")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_data:
        await update.message.reply_text("Спочатку виберіть дію через /start")
        return

    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_{user_id}.jpg"
    await photo_file.download_to_drive(file_path)
    user_data[user_id]["photo"] = file_path

    action = user_data[user_id]["action"]
    if action == "expand":
        keyboard = [
            [InlineKeyboardButton("1024x1024", callback_data="size_1024")],
            [InlineKeyboardButton("1920x1080", callback_data="size_1920")],
            [InlineKeyboardButton("2048x1024", callback_data="size_2048")]
        ]
        await update.message.reply_text("Виберіть розмір:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        image_bytes = send_to_image_service(file_path, action="enhance")
        await update.message.reply_photo(photo=BytesIO(image_bytes), caption="Готово ✅")

async def size_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    file_path = user_data[user_id]["photo"]
    size = int(query.data.split("_")[1])

    await query.edit_message_text("Фото обробляється, зачекайте ⏳")

    image_bytes = send_to_image_service(file_path, action="expand", size=size)

    await context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=BytesIO(image_bytes),
        caption="Готово ✅"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="^(expand|enhance)$"))
    app.add_handler(CallbackQueryHandler(size_choice, pattern="^size_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()
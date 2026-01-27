import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Завантажуємо змінні з .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

user_data = {}  # Зберігати стан користувача

# 1️⃣ Старт і кнопки
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[INFO] Користувач {update.message.from_user.username} запустив /start")
    keyboard = [
        [InlineKeyboardButton("Розширити + покращити", callback_data="expand")],
        [InlineKeyboardButton("Просто покращити", callback_data="enhance")]
    ]
    await update.message.reply_text("Виберіть дію:", reply_markup=InlineKeyboardMarkup(keyboard))

# 2️⃣ Користувач обрав дію
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    action = query.data
    print(f"[INFO] Користувач {query.from_user.username} вибрав дію: {action}")

    user_data[user_id] = {"action": action, "photo": None}
    await query.edit_message_text("Надішліть фото для обробки:")

# 3️⃣ Користувач надсилає фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    if user_id not in user_data:
        print(f"[WARNING] Користувач {username} надіслав фото без вибору дії")
        await update.message.reply_text("Спочатку виберіть дію через /start")
        return

    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_{user_id}.jpg"
    await photo_file.download_to_drive(file_path)
    user_data[user_id]["photo"] = file_path
    print(f"[INFO] Користувач {username} надіслав фото: {file_path}")

    action = user_data[user_id]["action"]
    if action == "expand":
        keyboard = [
            [InlineKeyboardButton("1024x1024", callback_data="size_1024")],
            [InlineKeyboardButton("1920x1080", callback_data="size_1920")],
            [InlineKeyboardButton("2048x1024", callback_data="size_2048")]
        ]
        await update.message.reply_text("Виберіть розмір:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_photo(photo=open(file_path, "rb"), caption="Тест: фото отримано та оброблено (без ШІ)")

# 4️⃣ Обробка вибору розміру
async def size_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    file_path = user_data[user_id]["photo"]
    size = query.data.split("_")[1]
    username = query.from_user.username
    print(f"[INFO] Користувач {username} вибрав розмір {size}x{size}")

    await query.edit_message_text(f"Тест: фото отримано, вибрано розмір {size}x{size}")
    await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(file_path, "rb"))

# 🔹 Основне
print("[INFO] Запуск бота...")
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button, pattern="^(expand|enhance)$"))
app.add_handler(CallbackQueryHandler(size_choice, pattern="^size_"))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.run_polling()

import os
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# 🔹 Зчитуємо змінні середовища з Render
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
ADMIN_ID = os.getenv("ADMIN_ID")

print("=== DEBUG INFO ===")
print("BOT_TOKEN:", BOT_TOKEN)
print("GROUP_ID:", GROUP_ID)
print("ADMIN_ID:", ADMIN_ID)
print("===================")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не знайдено! Перевір Environment Variables у Render!")

# 🔹 Flask застосунок для підтримки живого процесу
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running!"

# 🔹 Основна логіка бота
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_message = update.message.text
    user = update.message.from_user

    # Видаляємо повідомлення користувача
    try:
        await update.message.delete()
    except Exception as e:
        print("❌ Не вдалося видалити повідомлення:", e)

    # Відправляємо користувачу повідомлення про модерацію
    msg = await update.message.reply_text("🕓 Ваше повідомлення відправлено на модерацію.")
    await asyncio.sleep(5)
    try:
        await msg.delete()
    except:
        pass

    # Відправляємо адміну повідомлення на схвалення
    keyboard = [
        [
            InlineKeyboardButton("✅ Схвалити", callback_data=f"approve|{user.id}|{user_message}"),
            InlineKeyboardButton("❌ Відхилити", callback_data=f"reject|{user.id}|{user_message}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"📝 Повідомлення від @{user.username or user.first_name}:\n\n{user_message}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=text, reply_markup=reply_markup)

# 🔹 Обробка кнопок (схвалити/відхилити)
async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    action = data[0]
    user_id = data[1]
    user_message = data[2]

    if action == "approve":
        await context.bot.send_message(chat_id=GROUP_ID, text=user_message)
        await query.edit_message_text("✅ Повідомлення схвалено та опубліковано.")
    else:
        await query.edit_message_text("❌ Повідомлення відхилено.")

# 🔹 Запуск Telegram бота
async def run_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(callback_query))

    print("🤖 Бот запущено успішно!")
    await application.run_polling()

# 🔹 Головний вхід
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

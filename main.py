import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from aiohttp import web
import threading

# === 🔹 Налаштування ===
TOKEN = os.environ.get("BOT_TOKEN")  # свій токен з Render environment
GROUP_ID = int(os.environ.get("GROUP_ID"))  # ID групи, наприклад -1001234567890

# === 🔹 Обробка нових повідомлень ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.chat.id == GROUP_ID:
        user = update.message.from_user
        text = update.message.text or "(немає тексту)"

        # Видаляємо повідомлення з групи
        await update.message.delete()

        # Повідомляємо користувача
        info_message = await update.message.reply_text("Ваше повідомлення відправлено на модерацію ✅")
        await asyncio.sleep(5)
        await info_message.delete()

        # Надсилаємо адміну для модерації
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Схвалити", callback_data=f"approve|{user.id}|{text}"),
                InlineKeyboardButton("❌ Відхилити", callback_data=f"reject|{user.id}")
            ]
        ])

        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"Повідомлення від @{user.username or user.full_name}:\n\n{text}",
            reply_markup=keyboard
        )

# === 🔹 Обробка натискання кнопок ===
async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    action = data[0]
    user_id = data[1]

    if action == "approve":
        text = data[2]
        await context.bot.send_message(chat_id=GROUP_ID, text=f"✅ {text}")
        await query.edit_message_text("✅ Повідомлення схвалено!")
    elif action == "reject":
        await query.edit_message_text("❌ Повідомлення відхилено!")

# === 🔹 Вебсервер для Render ===
async def handle(request):
    return web.Response(text="Bot is running!")

async def run_web():
    app = web.Application()
    app.router.add_get('/', handle)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

def start_web():
    import asyncio
    asyncio.run(run_web())

threading.Thread(target=start_web).start()

# === 🔹 Запуск бота ===
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(callback_query))

    print("✅ Бот запущений і працює!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

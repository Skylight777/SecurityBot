import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# 🔹 Твій токен бота
TOKEN = os.getenv("BOT_TOKEN")

# 🔹 ID чату адміністратора (кому приходять повідомлення на модерацію)
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# 🔹 ID групи, куди публікуються схвалені повідомлення
GROUP_ID = int(os.getenv("GROUP_ID"))

# 🧠 /start команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привіт! Я бот для модерації повідомлень у групі.")

# 🧠 Обробка нових повідомлень у групі
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    message_id = update.message.message_id

    # Зберігаємо дані про повідомлення
    context.user_data[message_id] = {
        "user_id": user.id,
        "username": user.username or user.first_name,
        "text": text
    }

    # Кнопки схвалення/відхилення
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Схвалити", callback_data=f"approve|{message_id}"),
            InlineKeyboardButton("❌ Відхилити", callback_data=f"reject|{message_id}")
        ]
    ])

    # Надсилаємо адміну
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Нове повідомлення від @{user.username or user.first_name}:\n\n{text}",
        reply_markup=keyboard
    )

    # Видаляємо оригінальне повідомлення
    await update.message.delete()

    # Тимчасове повідомлення користувачу
    reply = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"@{user.username or user.first_name}, ваше повідомлення було відправлено на модерацію ✅"
    )

    # Чекаємо 5 секунд і видаляємо повідомлення
    await asyncio.sleep(5)
    await reply.delete()

# 🧠 Обробка натискання кнопок (модерація)
async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, message_id_str = query.data.split("|")
    message_id = int(message_id_str)

    # Дістаємо дані
    data = context.user_data.get(message_id)
    if not data:
        await query.answer("Дані не знайдено ❌", show_alert=True)
        return

    username = data["username"]
    text = data["text"]

    if action == "approve":
        # Надсилаємо у групу схвалене повідомлення
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"📩 Повідомлення від @{username}:\n\n{text}"
        )
        await query.answer("✅ Схвалено")
    elif action == "reject":
        await query.answer("❌ Відхилено")

    # Видаляємо повідомлення з кнопками після вибору
    await query.message.delete()

# 🚀 Запуск бота
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Зберігаємо ID в контекст
    app.bot_data["ADMIN_ID"] = ADMIN_ID
    app.bot_data["GROUP_ID"] = GROUP_ID

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_message))
    app.add_handler(CallbackQueryHandler(callback_query))

    app.run_polling()

if __name__ == "__main__":
    main()

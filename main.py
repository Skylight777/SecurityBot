import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# 🔹 Отримуємо дані з Environment Variables (Render)
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))

# 🔹 Обробник нових повідомлень у групі
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # 1️⃣ Надіслати адміну повідомлення для модерації
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Схвалити", callback_data=f"approve|{user.id}|{text}"),
            InlineKeyboardButton("❌ Відхилити", callback_data="reject")
        ]
    ])
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"Нове повідомлення від @{user.username or user.first_name}:\n\n{text}",
        reply_markup=keyboard
    )

    # 2️⃣ Видалити оригінальне повідомлення з групи
    await update.message.delete()

    # 3️⃣ Надіслати користувачу повідомлення про модерацію
    reply = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"@{user.username or user.first_name}, ваше повідомлення було відправлено на модерацію ✅"
    )

    # 4️⃣ Зачекати 5 секунд і видалити це повідомлення
    await asyncio.sleep(5)
    await reply.delete()

# 🔹 Обробка натискання кнопок (модерація)
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    action = data[0]

    if action == "approve":
        user_id = data[1]
        text = data[2]
        # Публікуємо схвалене повідомлення назад у групу
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
        await query.edit_message_text("✅ Повідомлення схвалене й опубліковане.")
    elif action == "reject":
        await query.edit_message_text("❌ Повідомлення відхилене.")

# 🔹 Створюємо застосунок
app = ApplicationBuilder().token(TOKEN).build()

# 🔹 Реєструємо обробники
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
app.add_handler(CallbackQueryHandler(button_callback))

# 🔹 Запускаємо бота
app.run_polling()

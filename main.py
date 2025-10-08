# main.py
# Простий Telegram-модераційний бот (webhook + FastAPI)
# Пояснення та інструкції — у README.md
import os
import logging
import uuid
from http import HTTPStatus
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# Змінні середовища (в Render додаємо значення в Dashboard → Environment)
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # наприклад: https://your-service.onrender.com/

if not TOKEN or not ADMIN_ID or not GROUP_ID or not WEBHOOK_URL:
    logging.warning("Не всі змінні середовища встановлені. Перевірте TELEGRAM_TOKEN, ADMIN_ID, GROUP_ID, WEBHOOK_URL.")

# Словник очікуваних повідомлень (тимчасово в пам'яті)
PENDING = {}  # {uid: {"user": {...}, "text": "..."}}

# --- Handlers ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот працює. Повідомлення з групи потрапляють у чергу модерації.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Коли користувач пише в групі — зберігаємо повідомлення й надсилаємо адміну
    if not update.message:
        return
    user = update.effective_user
    text = update.message.text or "<не-текстовий контент>"
    uid = str(uuid.uuid4())
    PENDING[uid] = {
        "user": {"id": user.id, "username": user.username, "name": user.full_name},
        "text": text,
    }

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Схвалити", callback_data=f"approve|{uid}"),
         InlineKeyboardButton("❌ Відхилити", callback_data=f"reject|{uid}")]
    ])

    # Надсилаємо адміну (особисте повідомлення)
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Нове повідомлення від @{user.username or user.full_name} (id:{user.id}):\n\n{text}",
            reply_markup=kb,
        )
    except Exception as e:
        logging.exception("Не вдалося надіслати адміну повідомлення: %s", e)

    # Видаляємо оригінал з групи (щоб не з'являлося до схвалення)
    try:
        await update.message.delete()
    except Exception:
        pass

async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = (query.data or "").split("|")
    action = data[0]
    uid = data[1] if len(data) > 1 else None

    if action == "approve" and uid and uid in PENDING:
        payload = PENDING.pop(uid)
        text = f"{payload['text']}\n\n— від @{payload['user']['username'] or payload['user']['name']}"
        await context.bot.send_message(chat_id=GROUP_ID, text=text)
        await query.edit_message_text("✅ Повідомлення схвалене й опубліковане.")
    elif action == "reject":
        if uid and uid in PENDING:
            PENDING.pop(uid)
        await query.edit_message_text("❌ Повідомлення відхилено.")
    else:
        await query.edit_message_text("❗ Повідомлення не знайдено або вже оброблене.")

# --- Build application ---
app_ptb = Application.builder().token(TOKEN).build()
app_ptb.add_handler(CommandHandler("start", start_cmd))
app_ptb.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
app_ptb.add_handler(CallbackQueryHandler(callback_query))

# --- FastAPI зі lifespan для реєстрації webhook ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Регіструємо webhook у Telegram
    try:
        await app_ptb.bot.set_webhook(WEBHOOK_URL)
    except Exception as e:
        logging.exception("Помилка при set_webhook: %s", e)
    async with app_ptb:
        await app_ptb.start()
        yield
        await app_ptb.stop()

api = FastAPI(lifespan=lifespan)

@api.post("/")
async def process_update(request: Request):
    req = await request.json()
    update = Update.de_json(req, app_ptb.bot)
    await app_ptb.process_update(update)
    return Response(status_code=HTTPStatus.OK)

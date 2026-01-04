import os
import json
import logging
import asyncio
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================= CONFIGURATION =================
TOKEN = "8334336028:AAGuHATR6WWZY9R8falODGMniNh76TeVOyk"
ADMIN_ID = 900416774
CHANNEL_ID = -1003687270731

# ================= FLASK KEEP-ALIVE SERVER =================
app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>GyanPi Bot is Running 24/7! 🚀</h1>"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# ================= BOT LOGIC =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Global Data Store (Synced with Channel Pinned Msg)
users_db = {} 
DB_PIN_ID = None  # To store the message ID of the JSON database in channel

async def get_database(bot):
    """Channel ke pinned message se data fetch karta hai"""
    global users_db, DB_PIN_ID
    try:
        chat = await bot.get_chat(CHANNEL_ID)
        if chat.pinned_message and chat.pinned_message.text.startswith("DB_START|"):
            raw_data = chat.pinned_message.text.replace("DB_START|", "")
            users_db = json.loads(raw_data)
            DB_PIN_ID = chat.pinned_message.message_id
            logging.info(f"Database Loaded: {len(users_db)} users")
        else:
            logging.info("No Database found, creating new.")
            users_db = {}
            await save_database(bot)
    except Exception as e:
        logging.error(f"DB Load Error: {e}")

async def save_database(bot):
    """Channel pe pinned message ko update karta hai (Persistence)"""
    global DB_PIN_ID
    data_str = "DB_START|" + json.dumps(users_db)
    
    try:
        if DB_PIN_ID:
            try:
                await bot.edit_message_text(
                    chat_id=CHANNEL_ID,
                    message_id=DB_PIN_ID,
                    text=data_str
                )
                return
            except Exception:
                pass # Message might be deleted, send new one
        
        msg = await bot.send_message(CHANNEL_ID, data_str)
        await bot.pin_chat_message(CHANNEL_ID, msg.message_id)
        DB_PIN_ID = msg.message_id
        logging.info("Database Saved to Channel")
        
    except Exception as e:
        logging.error(f"DB Save Error: {e}")

# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **GyanPi Advanced Bot**\n\n"
        "✅ System Online\n"
        "✅ Database Connected\n"
        "✅ Flask Server Running\n\n"
        "Connect your Web App now!",
        parse_mode=ParseMode.MARKDOWN
    )
    # Refresh DB on start
    await get_database(context.bot)

async def channel_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listens to WebApp commands sent to Channel"""
    if not update.channel_post or update.channel_post.chat.id != CHANNEL_ID:
        return

    text = update.channel_post.text or ""
    
    # 1. REGISTER COMMAND FROM WEB APP
    # Format: REG|Name|Mobile|Pass
    if text.startswith("REG|"):
        try:
            _, name, mobile, password = text.split("|", 3)
            
            # Update DB
            users_db[mobile] = {
                "name": name,
                "pass": password,
                "friends": [],
                "requests": []
            }
            
            # Save to Pinned Message (Permanent Storage)
            await save_database(context.bot)
            
            # Broadcast update to all WebApps
            await context.bot.send_message(
                CHANNEL_ID, 
                f"SYS_UPDATE|USER_ADDED|{mobile}|{name}"
            )
            logging.info(f"New User Registered: {name}")
            
        except Exception as e:
            logging.error(f"Register Error: {e}")

    # 2. FRIEND REQUEST
    # Format: REQ|SenderMobile|TargetMobile
    elif text.startswith("REQ|"):
        try:
            _, sender, target = text.split("|")
            if target in users_db:
                # Add to DB requests if needed, but primarily WebApp handles local state
                # We broadcast the event so Target's app can see it
                pass 
        except: pass

    # 3. ADMIN MESSAGE
    elif text.startswith("ADMIN_MSG|"):
        try:
            _, mobile, msg = text.split("|", 2)
            # Send Telegram DM if user exists in bot context (Limitations apply)
            # For now, we broadcast to channel specifically for that user
            await context.bot.send_message(CHANNEL_ID, f"SYS_MSG|{mobile}|{msg}")
        except: pass

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    # Reload latest data
    await get_database(context.bot)
    
    msg = "👥 **Registered Users:**\n\n"
    for m, d in users_db.items():
        msg += f"📱 `{m}`\n👤 {d['name']}\n🔑 `{d['pass']}`\n\n"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

# ================= MAIN EXECUTION =================
if __name__ == "__main__":
    # 1. Start Flask in separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 2. Start Telegram Bot
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", admin_users))
    
    # Critical Handler for Channel Sync
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_listener))

    print("🚀 BOT + SERVER STARTED SUCCESSFULLY")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

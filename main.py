import os
import logging
import threading
import json
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIGURATION =================
TOKEN = "8334336028:AAGuHATR6WWZY9R8falODGMniNh76TeVOyk"
ADMIN_ID = 900416774
CHANNEL_ID = -1003687270731

# ================= INITIALIZE BOT =================
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

# ================= DATABASE =================
users_db = {}  # In-memory DB

# ================= FLASK SERVER (KEEP ALIVE) =================
app = Flask(__name__)

@app.route('/')
def index():
    return f"<h1>✅ Bot is Running!</h1><p>Users: {len(users_db)}</p>"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ================= BOT COMMANDS =================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    print(f"Command /start from {user.first_name}")  # Log to console
    
    if user.id == ADMIN_ID:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("👥 Users", callback_data="users"),
                   InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"))
        
        bot.reply_to(message, 
            f"👑 *ADMIN PANEL*\n\n"
            f"Welcome Boss! System is active.\n"
            f"👥 Connected Users: {len(users_db)}", 
            reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🌐 Open Web App", url="https://gyanpi-chat.netlify.app")) # Replace with your link
        
        bot.reply_to(message,
            f"🤖 *GyanPi Chat Bot*\n\n"
            f"Hi {user.first_name}!\n"
            f"I connect the Web App to Telegram.\n\n"
            f"👇 Click below to start chatting!",
            reply_markup=markup)

@bot.message_handler(commands=['users'])
def admin_users(message):
    if message.from_user.id != ADMIN_ID: return
    
    if not users_db:
        bot.reply_to(message, "📭 No registered users yet.")
        return
        
    msg = "👥 *REGISTERED USERS*\n\n"
    for mobile, data in users_db.items():
        msg += f"📱 `{mobile}`\n👤 {data.get('name')}\n🔑 `{data.get('pass')}`\n\n"
    
    # Split message if too long
    if len(msg) > 4000:
        bot.reply_to(message, msg[:4000])
    else:
        bot.reply_to(message, msg)

@bot.message_handler(commands=['msg'])
def admin_msg(message):
    if message.from_user.id != ADMIN_ID: return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "Usage: `/msg 9876543210 Hello`")
            return
            
        mobile, text = parts[1], parts[2]
        
        # Send to Channel (Web App listens to this)
        bot.send_message(CHANNEL_ID, f"ADMIN_MSG|{mobile}|{text}")
        bot.reply_to(message, f"✅ Message sent to {mobile}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ================= CALLBACK QUERY =================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "users":
        if not users_db:
            bot.answer_callback_query(call.id, "No users yet!")
            return
        
        msg = "👥 *USERS LIST*\n\n"
        for m, d in users_db.items():
            msg += f"• `{m}` - {d.get('name')}\n"
        
        bot.send_message(call.message.chat.id, msg)
        bot.answer_callback_query(call.id)
        
    elif call.data == "broadcast":
        bot.send_message(call.message.chat.id, "Use command: `/broadcast Your Message`")
        bot.answer_callback_query(call.id)

# ================= CHANNEL LISTENER (WEBHOOK SIMULATION) =================
@bot.channel_post_handler(func=lambda m: m.chat.id == CHANNEL_ID)
def listen_channel(message):
    if not message.text: return
    
    text = message.text
    print(f"Channel Data: {text}") # Debug log
    
    parts = text.split("|")
    cmd = parts[0]
    
    if cmd == "REG" and len(parts) >= 4:
        name, mobile, pwd = parts[1], parts[2], parts[3]
        users_db[mobile] = {"name": name, "pass": pwd}
        
        # Notify Admin
        try:
            bot.send_message(ADMIN_ID, f"🆕 *New User Registered*\n\n👤 {name}\n📱 `{mobile}`")
        except: pass

    elif cmd == "FREQ" and len(parts) >= 3:
        pass # Friend request logic handled by Web App mostly

# ================= MAIN EXECUTION =================
if __name__ == "__main__":
    # 1. Start Flask in Background Thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask Server Started")

    # 2. Start Bot Polling (Blocks main thread, keeps alive)
    print("✅ Bot Polling Started...")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"❌ Critical Error: {e}")

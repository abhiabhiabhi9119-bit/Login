import os
import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# ================= CONFIG =================
TOKEN = "8334336028:AAGuHATR6WWZY9R8falODGMniNh76TeVOyk"
ADMIN_ID = 900416774
CHANNEL_ID = -1003687270731

# ================= LOGGING =================
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= DATABASE =================
users_db = {}

# ================= FLASK =================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return f'''
    <html>
    <head><title>GyanPi Bot</title>
    <style>
        body {{ font-family: Arial; text-align: center; padding: 50px; 
               background: linear-gradient(135deg, #667eea, #764ba2); 
               color: white; min-height: 100vh; margin: 0; }}
        .box {{ background: rgba(255,255,255,0.2); padding: 30px; 
               border-radius: 20px; max-width: 400px; margin: 20px auto; }}
    </style>
    </head>
    <body>
        <h1>🤖 GyanPi Bot</h1>
        <div class="box">
            <h2>✅ Bot is ONLINE</h2>
            <p>👥 Users: {len(users_db)}</p>
            <p>📡 Channel: Connected</p>
        </div>
        <div class="box">
            <h3>Admin Commands</h3>
            <p>/start - Main Menu</p>
            <p>/users - All Users</p>
            <p>/msg mobile text - Send Message</p>
            <p>/broadcast text - Send to All</p>
            <p>/changepass mobile pass - Change Password</p>
            <p>/delete mobile - Delete User</p>
        </div>
    </body>
    </html>
    '''

@flask_app.route('/health')
def health():
    return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ================= HANDLERS =================

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("👥 All Users", callback_data="users")],
            [InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("📢 Broadcast Help", callback_data="bcast")]
        ]
        update.message.reply_text(
            f"👑 *ADMIN PANEL*\n\n"
            f"Hello {user.first_name}!\n\n"
            f"📊 Users: {len(users_db)}\n"
            f"🤖 Status: Online",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            f"🤖 *GyanPi Chat Bot*\n\n"
            f"Welcome {user.first_name}!\n\n"
            f"Use our Web App to register and chat with friends!",
            parse_mode='Markdown'
        )

def users_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Admin only!")
        return
    
    if not users_db:
        update.message.reply_text("📭 No users yet!")
        return
    
    msg = "👥 *ALL USERS*\n\n"
    for i, (mobile, data) in enumerate(users_db.items(), 1):
        msg += f"{i}. `{mobile}`\n"
        msg += f"   Name: {data.get('name', 'N/A')}\n"
        msg += f"   Pass: `{data.get('pass', 'N/A')}`\n\n"
    
    update.message.reply_text(msg, parse_mode='Markdown')

def msg_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Admin only!")
        return
    
    if len(context.args) < 2:
        update.message.reply_text("Usage: /msg 9876543210 Hello User")
        return
    
    mobile = context.args[0]
    message = " ".join(context.args[1:])
    
    try:
        context.bot.send_message(CHANNEL_ID, f"ADMIN_MSG|{mobile}|{message}")
        update.message.reply_text(f"✅ Sent to {mobile}")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")

def broadcast_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        update.message.reply_text("Usage: /broadcast Hello Everyone!")
        return
    
    message = " ".join(context.args)
    
    try:
        context.bot.send_message(CHANNEL_ID, f"BROADCAST|{message}")
        update.message.reply_text(f"📢 Broadcast sent!")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")

def changepass_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Admin only!")
        return
    
    if len(context.args) != 2:
        update.message.reply_text("Usage: /changepass 9876543210 newpass123")
        return
    
    mobile, newpass = context.args
    
    if mobile in users_db:
        users_db[mobile]['pass'] = newpass
        context.bot.send_message(CHANNEL_ID, f"PASS_CHANGE|{mobile}|{newpass}")
        update.message.reply_text(f"✅ Password changed for {mobile}")
    else:
        update.message.reply_text(f"❌ User not found!")

def delete_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("❌ Admin only!")
        return
    
    if not context.args:
        update.message.reply_text("Usage: /delete 9876543210")
        return
    
    mobile = context.args[0]
    
    if mobile in users_db:
        del users_db[mobile]
        context.bot.send_message(CHANNEL_ID, f"USER_DELETE|{mobile}")
        update.message.reply_text(f"✅ Deleted {mobile}")
    else:
        update.message.reply_text(f"❌ Not found!")

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "users":
        if not users_db:
            query.edit_message_text("📭 No users yet!")
            return
        msg = "👥 *USERS*\n\n"
        for m, d in users_db.items():
            msg += f"• `{m}` - {d.get('name','N/A')}\n"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == "stats":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        query.edit_message_text(
            f"📊 *STATS*\n\n👥 Users: {len(users_db)}\n🤖 Bot: Online",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "bcast":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        query.edit_message_text(
            "📢 *BROADCAST*\n\nUse: `/broadcast Your message`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "back":
        keyboard = [
            [InlineKeyboardButton("👥 All Users", callback_data="users")],
            [InlineKeyboardButton("📊 Stats", callback_data="stats")],
            [InlineKeyboardButton("📢 Broadcast Help", callback_data="bcast")]
        ]
        query.edit_message_text(
            f"👑 *ADMIN PANEL*\n\n📊 Users: {len(users_db)}\n🤖 Status: Online",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

def channel_msg(update: Update, context: CallbackContext):
    if not update.channel_post:
        return
    if update.channel_post.chat.id != CHANNEL_ID:
        return
    
    text = update.channel_post.text or ""
    parts = text.split("|")
    cmd = parts[0] if parts else ""
    
    logger.info(f"Channel: {text[:50]}")
    
    if cmd == "REG" and len(parts) >= 4:
        name, mobile, pwd = parts[1], parts[2], parts[3]
        users_db[mobile] = {"name": name, "pass": pwd, "friends": [], "requests": []}
        logger.info(f"New user: {name}")
        try:
            context.bot.send_message(ADMIN_ID, f"🆕 New User!\n\n👤 {name}\n📱 `{mobile}`", parse_mode='Markdown')
        except:
            pass
    
    elif cmd == "FREQ" and len(parts) >= 3:
        sender, target = parts[1], parts[2]
        if target in users_db:
            if sender not in users_db[target].get('requests', []):
                users_db[target].setdefault('requests', []).append(sender)
    
    elif cmd == "FACC" and len(parts) >= 3:
        accepter, requester = parts[1], parts[2]
        if accepter in users_db:
            users_db[accepter].setdefault('friends', []).append(requester)
        if requester in users_db:
            users_db[requester].setdefault('friends', []).append(accepter)

def error(update, context):
    logger.error(f"Error: {context.error}")

# ================= MAIN =================
def main():
    # Flask thread
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    logger.info("Flask started")
    
    # Bot
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("users", users_cmd))
    dp.add_handler(CommandHandler("msg", msg_cmd))
    dp.add_handler(CommandHandler("broadcast", broadcast_cmd))
    dp.add_handler(CommandHandler("changepass", changepass_cmd))
    dp.add_handler(CommandHandler("delete", delete_cmd))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.chat_type.channel, channel_msg))
    dp.add_error_handler(error)
    
    logger.info("🚀 Bot Started!")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()

if __name__ == "__main__":
    main()

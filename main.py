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
            [InlineKeyboardButton("📊 Stats", callback_data="stats")]
        ]
        update.message.reply_text(
            f"👑 *ADMIN PANEL*\n\n"
            f"Hello {user.first_name}!\n"
            f"📊 Users: {len(users_db)}\n"
            f"🤖 Status: Online",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            f"🤖 *GyanPi Chat Bot*\n\n"
            f"Welcome {user.first_name}!\n"
            f"Use Web App to chat!",
            parse_mode='Markdown'
        )

def users_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not users_db:
        update.message.reply_text("📭 No users yet!")
        return
    
    msg = "👥 *ALL USERS*\n\n"
    for mobile, data in users_db.items():
        msg += f"📱 `{mobile}`\n👤 {data.get('name')}\n🔑 `{data.get('pass')}`\n\n"
    
    update.message.reply_text(msg, parse_mode='Markdown')

def msg_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if len(context.args) < 2:
        update.message.reply_text("Usage: /msg 9876543210 Hello")
        return
    
    mobile = context.args[0]
    message = " ".join(context.args[1:])
    context.bot.send_message(CHANNEL_ID, f"ADMIN_MSG|{mobile}|{message}")
    update.message.reply_text(f"✅ Sent to {mobile}")

def broadcast_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        update.message.reply_text("Usage: /broadcast Hello All!")
        return
    
    message = " ".join(context.args)
    context.bot.send_message(CHANNEL_ID, f"BROADCAST|{message}")
    update.message.reply_text("📢 Broadcast sent!")

def changepass_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if len(context.args) != 2:
        update.message.reply_text("Usage: /changepass 9876543210 newpass")
        return
    
    mobile, newpass = context.args
    if mobile in users_db:
        users_db[mobile]['pass'] = newpass
        context.bot.send_message(CHANNEL_ID, f"PASS_CHANGE|{mobile}|{newpass}")
        update.message.reply_text(f"✅ Changed for {mobile}")
    else:
        update.message.reply_text("❌ User not found!")

def delete_cmd(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        update.message.reply_text("Usage: /delete 9876543210")
        return
    
    mobile = context.args[0]
    if mobile in users_db:
        del users_db[mobile]
        context.bot.send_message(CHANNEL_ID, f"USER_DELETE|{mobile}")
        update.message.reply_text(f"✅ Deleted!")
    else:
        update.message.reply_text("❌ Not found!")

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == "users":
        if not users_db:
            query.edit_message_text("📭 No users!")
            return
        msg = "👥 *USERS*\n\n"
        for m, d in users_db.items():
            msg += f"• `{m}` - {d.get('name')}\n"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif query.data == "stats":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
        query.edit_message_text(f"📊 Users: {len(users_db)}", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("👥 All Users", callback_data="users")],
            [InlineKeyboardButton("📊 Stats", callback_data="stats")]
        ]
        query.edit_message_text(f"👑 *ADMIN PANEL*\n\n📊 Users: {len(users_db)}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

def channel_msg(update: Update, context: CallbackContext):
    if not update.channel_post or update.channel_post.chat.id != CHANNEL_ID:
        return
    
    text = update.channel_post.text or ""
    parts = text.split("|")
    cmd = parts[0]
    
    if cmd == "REG" and len(parts) >= 4:
        name, mobile, pwd = parts[1], parts[2], parts[3]
        users_db[mobile] = {"name": name, "pass": pwd, "friends": [], "requests": []}
        logger.info(f"New user: {name}")
        context.bot.send_message(ADMIN_ID, f"🆕 New User!\n👤 {name}\n📱 {mobile}")
    
    elif cmd == "FREQ" and len(parts) >= 3:
        sender, target = parts[1], parts[2]
        if target in users_db:
            users_db[target].setdefault('requests', []).append(sender)
    
    elif cmd == "FACC" and len(parts) >= 3:
        a, r = parts[1], parts[2]
        if a in users_db:
            users_db[a].setdefault('friends', []).append(r)
        if r in users_db:
            users_db[r].setdefault('friends', []).append(a)

# ================= MAIN =================
def main():
    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Flask started")
    
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
    
    logger.info("🚀 Bot Started!")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()

if __name__ == "__main__":
    main()

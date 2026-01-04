import os
import json
import logging
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ================= CONFIGURATION =================
TOKEN = "8334336028:AAGuHATR6WWZY9R8falODGMniNh76TeVOyk"
ADMIN_ID = 900416774
CHANNEL_ID = -1003687270731

# ================= LOGGING =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= DATABASE (In-Memory + Channel Sync) =================
users_db = {}  # {mobile: {name, pass, friends:[], requests:[]}}

# ================= FLASK KEEP-ALIVE =================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return f'''
    <html>
    <head><title>GyanPi Bot</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; min-height: 100vh;">
        <h1>🤖 GyanPi Bot is LIVE!</h1>
        <p>✅ Bot Status: Running</p>
        <p>👥 Total Users: {len(users_db)}</p>
        <p>🔗 Channel ID: {CHANNEL_ID}</p>
        <hr>
        <h3>Admin Commands:</h3>
        <p>/start - Start Bot</p>
        <p>/users - See All Users</p>
        <p>/msg mobile message - Send Message to User</p>
        <p>/broadcast message - Send to All Users</p>
    </body>
    </html>
    '''

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ================= HELPER FUNCTIONS =================
async def save_user_to_channel(context, mobile, name, password):
    """Save user data to channel"""
    try:
        msg = f"USER_DATA|{mobile}|{name}|{password}"
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)
        logger.info(f"Saved user to channel: {mobile}")
    except Exception as e:
        logger.error(f"Save error: {e}")

async def broadcast_to_channel(context, message):
    """Send any message to channel"""
    try:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=message)
    except Exception as e:
        logger.error(f"Broadcast error: {e}")

# ================= BOT COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Shows main menu"""
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("👥 All Users", callback_data="admin_users")],
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔄 Refresh Database", callback_data="admin_refresh")]
        ]
        await update.message.reply_text(
            f"👑 **ADMIN PANEL**\n\n"
            f"Welcome Boss! {user.first_name}\n\n"
            f"📊 Total Users: {len(users_db)}\n"
            f"🤖 Bot Status: Online\n\n"
            f"Select an option below:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📱 Register", callback_data="register")],
            [InlineKeyboardButton("🔑 Login", callback_data="login")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        await update.message.reply_text(
            f"🤖 **GyanPi Chat Bot**\n\n"
            f"Welcome {user.first_name}!\n\n"
            f"This bot connects with our Web App.\n"
            f"Register/Login using Web App at:\n"
            f"🌐 https://your-webapp-url.netlify.app\n\n"
            f"Or use buttons below:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to see all users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not users_db:
        await update.message.reply_text("📭 No users registered yet!")
        return
    
    msg = "👥 **ALL REGISTERED USERS**\n\n"
    for i, (mobile, data) in enumerate(users_db.items(), 1):
        msg += f"{i}. 📱 `{mobile}`\n"
        msg += f"   👤 Name: {data.get('name', 'N/A')}\n"
        msg += f"   🔑 Pass: `{data.get('pass', 'N/A')}`\n"
        msg += f"   👫 Friends: {len(data.get('friends', []))}\n\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def msg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to send message to specific user"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /msg <mobile> <message>\n"
            "Example: /msg 9876543210 Hello User!"
        )
        return
    
    mobile = context.args[0]
    message = " ".join(context.args[1:])
    
    if mobile not in users_db:
        await update.message.reply_text(f"❌ User {mobile} not found!")
        return
    
    # Send to channel so web app can pick it up
    await broadcast_to_channel(context, f"ADMIN_MSG|{mobile}|{message}")
    await update.message.reply_text(f"✅ Message sent to {mobile}:\n\n{message}")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to broadcast to all users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    
    # Send to channel for all users
    await broadcast_to_channel(context, f"BROADCAST|{message}")
    await update.message.reply_text(f"📢 Broadcast sent to {len(users_db)} users:\n\n{message}")

async def changepass_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to change user password"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /changepass <mobile> <newpassword>")
        return
    
    mobile, newpass = context.args
    
    if mobile not in users_db:
        await update.message.reply_text(f"❌ User {mobile} not found!")
        return
    
    users_db[mobile]['pass'] = newpass
    await broadcast_to_channel(context, f"PASS_CHANGE|{mobile}|{newpass}")
    await update.message.reply_text(f"✅ Password changed for {mobile}")

async def delete_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to delete user"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /delete <mobile>")
        return
    
    mobile = context.args[0]
    
    if mobile in users_db:
        del users_db[mobile]
        await broadcast_to_channel(context, f"USER_DELETE|{mobile}")
        await update.message.reply_text(f"✅ User {mobile} deleted!")
    else:
        await update.message.reply_text(f"❌ User {mobile} not found!")

# ================= CALLBACK HANDLERS =================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "admin_users":
        if not users_db:
            await query.edit_message_text("📭 No users registered yet!")
            return
        
        msg = "👥 **ALL USERS**\n\n"
        for mobile, info in users_db.items():
            msg += f"📱 `{mobile}` - {info.get('name', 'N/A')}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_admin")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == "admin_stats":
        total = len(users_db)
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_admin")]]
        await query.edit_message_text(
            f"📊 **STATISTICS**\n\n"
            f"👥 Total Users: {total}\n"
            f"🤖 Bot: Online\n"
            f"📡 Channel: Connected",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "admin_broadcast":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_admin")]]
        await query.edit_message_text(
            "📢 **BROADCAST**\n\n"
            "Use command:\n"
            "`/broadcast Your message here`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "admin_refresh":
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_admin")]]
        await query.edit_message_text(
            f"🔄 **DATABASE REFRESHED**\n\n"
            f"Current Users: {len(users_db)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "back_admin":
        keyboard = [
            [InlineKeyboardButton("👥 All Users", callback_data="admin_users")],
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")]
        ]
        await query.edit_message_text(
            f"👑 **ADMIN PANEL**\n\n"
            f"📊 Total Users: {len(users_db)}\n"
            f"🤖 Bot Status: Online",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "register":
        await query.edit_message_text(
            "📱 **REGISTRATION**\n\n"
            "Please use our Web App to register:\n"
            "🌐 https://your-webapp.netlify.app\n\n"
            "Or send: /register Name Mobile Password"
        )
    
    elif data == "login":
        await query.edit_message_text(
            "🔑 **LOGIN**\n\n"
            "Please use our Web App to login:\n"
            "🌐 https://your-webapp.netlify.app"
        )
    
    elif data == "help":
        await query.edit_message_text(
            "ℹ️ **HELP**\n\n"
            "This bot works with GyanPi Web App.\n\n"
            "1. Open Web App\n"
            "2. Register with Mobile & Password\n"
            "3. Login and chat with friends!\n\n"
            "🌐 https://your-webapp.netlify.app"
        )

# ================= CHANNEL MESSAGE HANDLER =================

async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages from channel (Web App sends here)"""
    if not update.channel_post:
        return
    
    if update.channel_post.chat.id != CHANNEL_ID:
        return
    
    text = update.channel_post.text
    if not text:
        return
    
    logger.info(f"Channel message: {text[:50]}...")
    
    # Parse different message types
    parts = text.split("|")
    msg_type = parts[0] if parts else ""
    
    # 1. NEW USER REGISTRATION
    if msg_type == "REG" and len(parts) >= 4:
        _, name, mobile, password = parts[0], parts[1], parts[2], parts[3]
        users_db[mobile] = {
            "name": name,
            "pass": password,
            "friends": [],
            "requests": []
        }
        logger.info(f"New user registered: {name} ({mobile})")
        
        # Notify admin
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🆕 **NEW USER REGISTERED**\n\n👤 {name}\n📱 {mobile}"
            )
        except:
            pass
    
    # 2. FRIEND REQUEST
    elif msg_type == "FREQ" and len(parts) >= 3:
        sender = parts[1]
        target = parts[2]
        if target in users_db:
            if 'requests' not in users_db[target]:
                users_db[target]['requests'] = []
            if sender not in users_db[target]['requests']:
                users_db[target]['requests'].append(sender)
        logger.info(f"Friend request: {sender} -> {target}")
    
    # 3. FRIEND ACCEPT
    elif msg_type == "FACC" and len(parts) >= 3:
        accepter = parts[1]
        requester = parts[2]
        
        # Add to friends list for both
        if accepter in users_db:
            if 'friends' not in users_db[accepter]:
                users_db[accepter]['friends'] = []
            if requester not in users_db[accepter]['friends']:
                users_db[accepter]['friends'].append(requester)
        
        if requester in users_db:
            if 'friends' not in users_db[requester]:
                users_db[requester]['friends'] = []
            if accepter not in users_db[requester]['friends']:
                users_db[requester]['friends'].append(accepter)
        
        logger.info(f"Friends now: {accepter} <-> {requester}")

# ================= MAIN =================

def main():
    """Start the bot"""
    # Start Flask in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server started")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("msg", msg_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("changepass", changepass_command))
    application.add_handler(CommandHandler("delete", delete_user_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_post_handler))
    
    # Start polling
    logger.info("🚀 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()

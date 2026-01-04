import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================= CONFIG =================
TOKEN = "8334336028:AAGuHATR6WWZY9R8falODGMniNh76TeVOyk"
ADMIN_ID = 900416774
CHANNEL_ID = -1003687270731

# In-memory database
users = {}

logging.basicConfig(level=logging.INFO)

# ================= HELPERS =================
async def save_to_channel(text: str):
    try:
        # Markdown parsing error avoid karne ke liye text mode plain rakhenge ya HTML
        await application.bot.send_message(CHANNEL_ID, text)
    except Exception as e:
        print(f"Save error: {e}")

def get_chat_key(m1: str, m2: str) -> str:
    return "_".join(sorted([m1, m2]))

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 GyanPi Private Chat\n\n"
        "✅ Bot is running perfectly!\n"
        "Deploy hone ke baad web app link yahan add karna."
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("❌ Usage: /register Name Mobile Password")
        return
    name, mobile, password = context.args
    
    if mobile in users:
        await update.message.reply_text("❌ Already registered!")
        return
    
    users[mobile] = {
        "name": name,
        "pass": password,
        "friends": [],
        "requests": [],
        "pending": []
    }
    await save_to_channel(f"NEW_USER|{mobile}|{name}|{password}")
    await update.message.reply_text(f"✅ Registered: {name}")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /login Mobile Password")
        return
    mobile, pwd = context.args
    
    if mobile not in users or users[mobile]["pass"] != pwd:
        await update.message.reply_text("❌ Login Failed")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 Users", callback_data="all_users")],
        [InlineKeyboardButton("👫 Friends", callback_data="my_friends")],
        [InlineKeyboardButton("➕ Requests", callback_data="requests")]
    ]
    await update.message.reply_text(f"✅ Welcome {users[mobile]['name']}", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= ADMIN =================
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = "👑 USERS:\n"
    for m, d in users.items():
        text += f"{m} : {d['name']} : {d['pass']}\n"
    await update.message.reply_text(text)

async def admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2: return
    mobile = context.args[0]
    msg = " ".join(context.args[1:])
    if mobile in users:
        await save_to_channel(f"ADMIN_MSG|{mobile}|{msg}")
        await update.message.reply_text("Sent!")

# ================= BUTTONS =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Simple mock user detection for buttons (since buttons don't pass args)
    # In real app, we use web app logic. Here mostly for testing.
    user_mobile = list(users.keys())[0] if users else None 

    if data == "all_users":
        text = "Users:\n" + "\n".join([f"{u}: {d['name']}" for u,d in users.items()])
        await query.edit_message_text(text or "No users")

# ================= CHANNEL SYNC =================
async def channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Channel posts come here
    if not update.channel_post or update.channel_post.chat.id != CHANNEL_ID:
        return
    text = update.channel_post.text or ""
    
    if text.startswith("NEW_USER|"):
        parts = text.split("|")
        if len(parts) >= 4:
            users[parts[1]] = {"name": parts[2], "pass": parts[3], "friends": [], "requests": [], "pending": []}

    elif text.startswith("ADMIN_MSG|"):
        parts = text.split("|", 2)
        if len(parts) == 3:
            mobile, msg = parts[1], parts[2]
            try:
                # Try to send DM if user has started bot
                # Note: Bot can't initiate chat with user ID unless user started bot
                # Here we simulate by just logging or if we had user_id mapped
                pass 
            except:
                pass

# ================= MAIN =================
if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("users", admin_users))
    application.add_handler(CommandHandler("msg", admin_msg))
    application.add_handler(CallbackQueryHandler(button))
    
    # !!! YE LINE AB 100% CORRECT HAI !!!
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, channel_handler))

    print("✅ Bot is Live on Render!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

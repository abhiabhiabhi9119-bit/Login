import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================= CONFIG =================
TOKEN = "8334336028:AAGuHATR6WWZY9R8falODGMniNh76TeVOyk"  # ← Deploy ke baad revoke kar lena
ADMIN_ID = 900416774
CHANNEL_ID = -1003687270731  # ← Tumhara private channel

# In-memory database
users = {}  # {mobile: {"name":.., "pass":.., "friends": [], "requests": [], "pending": []}}

logging.basicConfig(level=logging.INFO)

# ================= HELPERS =================
async def save_to_channel(text: str):
    try:
        await application.bot.send_message(CHANNEL_ID, text)
    except Exception as e:
        print("Channel save error:", e)

def get_chat_key(m1: str, m2: str) -> str:
    return "_".join(sorted([m1, m2]))

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 GyanPi Private Chat System\n\n"
        "📱 /register Name Mobile Password\n"
        "🔑 /login Mobile Password\n\n"
        "🌐 Web App: https://gyanpi-chat.netlify.app\n"
        "(Deploy karne ke baad yahan apna link daal dena)"
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("❌ Usage: /register Rohit 9123456789 mypass123")
        return
    name, mobile, password = context.args
    
    if mobile in users:
        await update.message.reply_text("❌ Ye mobile number already registered hai!")
        return
    
    users[mobile] = {
        "name": name,
        "pass": password,
        "friends": [],
        "requests": [],
        "pending": []
    }
    await save_to_channel(f"NEW_USER|{mobile}|{name}|{password}")
    await update.message.reply_text(f"✅ Registered Successfully!\n\nWelcome {name} ❤️\nAb /login karo")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /login 9123456789 mypass123")
        return
    mobile, pwd = context.args
    
    if mobile not in users:
        await update.message.reply_text("❌ Mobile number registered nahi hai!")
        return
    if users[mobile]["pass"] != pwd:
        await update.message.reply_text("❌ Password galat hai!")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="all_users")],
        [InlineKeyboardButton("👫 My Friends", callback_data="my_friends")],
        [InlineKeyboardButton("➕ Friend Requests", callback_data="requests")]
    ]
    await update.message.reply_text(
        f"✅ Login Successful!\nHello {users[mobile]['name']} 🔥",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= ADMIN COMMANDS =================
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = "👑 ALL USERS (Admin Only)\n\n"
    for mobile, data in users.items():
        text += f"`{mobile}` → {data['name']} → `{data['pass']}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /msg 9123456789 Hello user!")
        return
    mobile = context.args[0]
    message = " ".join(context.args[1:])
    if mobile not in users:
        await update.message.reply_text("❌ User not found!")
        return
    await save_to_channel(f"ADMIN_MSG|{mobile}|{message}")
    await update.message.reply_text(f"✅ Message sent to {mobile}")

# ================= BUTTON HANDLER =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Find logged-in user (temporary mapping using mobile length)
    user_mobile = None
    for mob, info in users.items():
        if update.effective_user.id in [900416774]:  # admin always allowed
            user_mobile = mob
            break
        # Simple check (later web app se proper login hoga)
        if len(mob) == 10 or len(mob) == 12:
            user_mobile = mob

    if data == "all_users":
        keyboard = []
        text = "👥 ALL USERS\n\n"
        for mob, info in users.items():
            if mob != user_mobile:
                text += f"• {info['name']} ({mob})\n"
                keyboard.append([InlineKeyboardButton(f"➕ Send Request → {info['name']}", callback_data=f"req_{mob}")])
        await query.edit_message_text(text if keyboard else "No other users", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "my_friends":
        friends = users.get(user_mobile, {}).get("friends", [])
        if not friends:
            await query.edit_message_text("😢 No friends yet\nPehle requests bhejo!")
            return
        keyboard = []
        for fmob in friends:
            name = users[fmob]["name"]
            chat_key = get_chat_key(user_mobile, fmob)
            keyboard.append([InlineKeyboardButton(f"💬 Chat with {name}", url=f"https://gyanpi-chat.netlify.app/chat.html?room={chat_key}")])
        await query.edit_message_text("👫 Your Friends", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "requests":
        reqs = users.get(user_mobile, {}).get("requests", [])
        if not reqs:
            await query.edit_message_text("📪 No pending requests")
            return
        keyboard = []
        for rmob in reqs:
            name = users[rmob]["name"]
            keyboard.append([InlineKeyboardButton(f"✅ Accept {name}", callback_data=f"accept_{rmob}")])
            keyboard.append([InlineKeyboardButton("❌ Reject", callback_data=f"reject_{rmob}")])
        await query.edit_message_text("➕ Friend Requests", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("req_"):
        target = data.split("_")[1]
        if target in users.get(user_mobile, {}).get("pending", []):
            await query.edit_message_text("⏳ Request already sent!")
            return
        users[user_mobile]["pending"].append(target)
        users[target]["requests"].append(user_mobile)
        await save_to_channel(f"FRIEND_REQ|{user_mobile}|{target}")
        await query.edit_message_text("✅ Friend Request Sent!")

    elif data.startswith("accept_"):
        sender = data.split("_")[1]
        users[user_mobile]["friends"].append(sender)
        users[sender]["friends"].append(user_mobile)
        # Clean up
        users[user_mobile]["requests"] = [x for x in users[user_mobile]["requests"] if x != sender]
        users[sender]["pending"] = [x for x in users[sender]["pending"] if x != user_mobile]
        await save_to_channel(f"FRIEND_ACCEPT|{sender}|{user_mobile}")
        await query.edit_message_text("✅ Friend Added! Ab chat kar sakte ho ❤️")

# ================= CHANNEL DATA SYNC =================
async def channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post or update.channel_post.chat.id != CHANNEL_ID:
        return
    text = update.channel_post.text or ""
    
    if text.startswith("NEW_USER|"):
        _, mobile, name, pwd = text.split("|", 3)
        users[mobile] = {"name": name, "pass": pwd, "friends": [], "requests": [], "pending": []}
    
    elif text.startswith("FRIEND_REQ|"):
        _, sender, target = text.split("|")
        if target in users and sender not in users[target]["requests"]:
            users[target]["requests"].append(sender)
    
    elif text.startswith("FRIEND_ACCEPT|"):
        _, u1, u2 = text.split("|")
        if u1 in users and u2 not in users[u1]["friends"]:
            users[u1]["friends"].append(u2)
        if u2 in users and u1 not in users[u2]["friends"]:
            users[u2]["friends"].append(u1)
    
    elif text.startswith("ADMIN_MSG|"):
        _, mobile, msg = text.split("|", 2)
        if mobile in users:
            try:
                await context.bot.send_message(int(mobile), f"📩 Admin Message:\n\n{msg}")
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
    
    # YE LINE SABSE IMPORTANT HAI – 100% WORKING
    application.add_handler(MessageHandler(filters.CHANNEL_POST, channel_handler))

    print("GyanPi Private Chat Bot is LIVE!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

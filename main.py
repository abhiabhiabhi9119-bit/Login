import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ================= CONFIG =================
TOKEN = "8334336028:AAGuHATR6WWZY9R8falODGMniNh76TeVOyk"  # ← Baad mein revoke kar lena
ADMIN_ID = 900416774
CHANNEL_ID = -1003687270731  # Private channel jahan data store hoga

# In-memory database
users = {}          # {mobile: {name, pass, friends[], requests[], pending[]}}
friend_chats = {}

logging.basicConfig(level=logging.INFO)

# ================= HELPERS =================
async def save_to_channel(text: str):
    try:
        await application.bot.send_message(CHANNEL_ID, text)
    except:
        pass

def get_chat_key(m1, m2):
    return "_".join(sorted([m1, m2]))

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 GyanPi Private Chat\n\n"
        "/register Name Mobile Password\n"
        "/login Mobile Password\n\n"
        "Web App: https://your-domain.com (deploy karne ke baad link yahan daal dena)"
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("❌ /register Name Mobile Password")
        return
    name, mobile, password = context.args
    if mobile in users:
        await update.message.reply_text("❌ Mobile already registered!")
        return
    users[mobile] = {
        "name": name,
        "pass": password,
        "friends": [],
        "requests": [],
        "pending": []
    }
    await save_to_channel(f"NEW_USER|{mobile}|{name}|{password}")
    await update.message.reply_text(f"✅ Registered!\nWelcome {name} ❤️\nNow /login karo")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("❌ /login Mobile Password")
        return
    mobile, pwd = context.args
    if mobile not in users or users[mobile]["pass"] != pwd:
        await update.message.reply_text("❌ Wrong mobile or password!")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="all_users")],
        [InlineKeyboardButton("👫 My Friends", callback_data="my_friends")],
        [InlineKeyboardButton("➕ Requests", callback_data="requests")]
    ]
    await update.message.reply_text(
        f"✅ Login Success!\nHello {users[mobile]['name']} 🔥",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= ADMIN COMMANDS =================
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = "👑 ALL USERS\n\n"
    for m, d in users.items():
        text += f"`{m}` → {d['name']} → `{d['pass']}`\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("/msg Mobile Message")
        return
    mobile = context.args[0]
    msg = " ".join(context.args[1:])
    if mobile not in users:
        await update.message.reply_text("User not found")
        return
    await save_to_channel(f"ADMIN_MSG|{mobile}|{msg}")
    await update.message.reply_text("✅ Message sent!")

# ================= BUTTONS =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    user_mobile = None
    for m, info in users.items():
        if str(update.effective_user.id) == m[:10]:  # temporary mapping
            user_mobile = m
            break

    if not user_mobile and data not in ["all_users"]:
        await query.edit_message_text("❌ Please /login first")
        return

    if data == "all_users":
        keyboard = []
        text = "👥 ALL USERS\n\n"
        for m, info in users.items():
            if m != user_mobile:
                text += f"• {info['name']} ({m})\n"
                keyboard.append([InlineKeyboardButton(f"Request → {info['name']}", callback_data=f"req_{m}")])
        await query.edit_message_text(text or "No users", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "my_friends":
        friends = users[user_mobile]["friends"]
        if not friends:
            await query.edit_message_text("No friends yet 😢")
            return
        keyboard = []
        for f in friends:
            name = users[f]["name"]
            chat_key = get_chat_key(user_mobile, f)
            keyboard.append([InlineKeyboardButton(f"💬 Chat with {name}", url=f"https://your-domain.com/chat.html?room={chat_key}")])
        await query.edit_message_text("👫 Your Friends", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "requests":
        reqs = users[user_mobile]["requests"]
        if not reqs:
            await query.edit_message_text("No pending requests")
            return
        keyboard = []
        for r in reqs:
            name = users[r]["name"]
            keyboard.append([InlineKeyboardButton(f"✅ Accept {name}", callback_data=f"accept_{r}")])
        await query.edit_message_text("➕ Friend Requests", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("req_"):
        target = data.split("_")[1]
        if target in users[user_mobile]["pending"]:
            await query.edit_message_text("⏳ Already sent!")
            return
        users[user_mobile]["pending"].append(target)
        users[target]["requests"].append(user_mobile)
        await save_to_channel(f"REQ|{user_mobile}|{target}")
        await query.edit_message_text("✅ Friend Request Sent!")

    elif data.startswith("accept_"):
        sender = data.split("_")[1]
        # Add friendship both sides
        users[user_mobile]["friends"].append(sender)
        users[sender]["friends"].append(user_mobile)
        # Clean requests
        users[user_mobile]["requests"] = [x for x in users[user_mobile]["requests"] if x != sender]
        users[sender]["pending"] = [x for x in users[sender]["pending"] if x != user_mobile]
        await save_to_channel(f"ACCEPT|{sender}|{user_mobile}")
        await query.edit_message_text("✅ Friend Added!")

# ================= CHANNEL DATA SYNC =================
async def channel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post or update.channel_post.chat.id != CHANNEL_ID:
        return
    text = update.channel_post.text
    if not text:
        return

    if text.startswith("NEW_USER|"):
        _, mobile, name, pwd = text.split("|", 3)
        users[mobile] = {"name": name, "pass": pwd, "friends": [], "requests": [], "pending": []}

    elif text.startswith("REQ|"):
        _, sender, target = text.split("|")
        if target in users and sender not in users[target]["requests"]:
            users[target]["requests"].append(sender)

    elif text.startswith("ACCEPT|"):
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
    application.add_handler(MessageHandler(filters.CHAT_TYPE.CHANNEL, channel_handler))

    print("🚀 GyanPi Bot is LIVE!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ================= CONFIG =================
TOKEN = "8334336028:AAGuHATR6WWZY9R8falODGMniNh76TeVOyk"  # Naya token bana lena bad mein
ADMIN_ID = 900416774  # Tumhara Telegram ID
CHANNEL_ID = -1003687270731  # Private Channel jahan data store hoga

# In-memory storage (Render pe restart hone pr bhi channel se load ho jayega)
users = {}          # {mobile: {"name":.., "pass":.., "friends": [], "requests": [], "pending": []}}
friend_chats = {}   # {chat_key: [user1_mobile, user2_mobile]}

# ================= BOT START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 Welcome!\n\n/register - Create Account\n/login - Login with Mobile & Password"
    )

# ================= REGISTER =================
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("❌ Usage: /register <name> <mobile> <password>")
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
    await update.message.reply_text(f"✅ Registered Successfully!\nWelcome {name} ❤️")

# ================= LOGIN =================
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /login <mobile> <password>")
        return
    mobile, password = context.args
    
    if mobile not in users:
        await update.message.reply_text("❌ Mobile not found!")
        return
    if users[mobile]["pass"] != password:
        await update.message.reply_text("❌ Wrong password!")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="all_users")],
        [InlineKeyboardButton("👫 My Friends", callback_data="my_friends")],
        [InlineKeyboardButton("➕ Friend Requests", callback_data="friend_requests")]
    ]
    await update.message.reply_text(
        f"✅ Login Successful!\nWelcome back {users[mobile]['name']} ❤️",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= ADMIN COMMANDS =================
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = "👑 ALL USERS (Mobile: Name: Password)\n\n"
    for mobile, data in users.items():
        text += f"`{mobile}` → {data['name']} → `{data['pass']}`\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /msg <mobile> <message>")
        return
    mobile = context.args[0]
    message = " ".join(context.args[1:])
    if mobile not in users:
        await update.message.reply_text("User not found!")
        return
    await save_to_channel(f"ADMIN_MSG|{mobile}|{message}")
    await update.message.reply_text(f"Sent to {mobile}")

async def change_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /changepass <mobile> <newpass>")
        return
    mobile, newpass = context.args
    if mobile not in users:
        await update.message.reply_text("Not found!")
        return
    users[mobile]["pass"] = newpass
    await save_to_channel(f"UPDATE_PASS|{mobile}|{newpass}")
    await update.message.reply_text(f"Password changed for {mobile}")

# ================= BUTTON HANDLERS =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "all_users":
        text = "👥 ALL USERS\n\n"
        for mobile, info in users.items():
            if mobile != "admin":
                btn = InlineKeyboardButton(f"{info['name']} ({mobile})", callback_data=f"send_req_{mobile}")
                keyboard = [[btn]]
                text += f"• {info['name']} ({mobile})\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard[:20]))
    
    elif data == "my_friends":
        user_mobile = await get_user_mobile(query.from_user.id)
        if not user_mobile:
            await query.edit_message_text("❌ Login first!")
            return
        friends = users[user_mobile]["friends"]
        if not friends:
            await query.edit_message_text("No friends yet 😢")
            return
        keyboard = []
        for f in friends:
            name = users[f]["name"]
            keyboard.append([InlineKeyboardButton(f"💬 Chat with {name}", callback_data=f"chat_{f}")])
        await query.edit_message_text("👫 Your Friends", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "friend_requests":
        user_mobile = await get_user_mobile(query.from_user.id)
        requests = users[user_mobile]["requests"]
        if not requests:
            await query.edit_message_text("No pending requests")
            return
        keyboard = []
        for req_mobile in requests:
            name = users[req_mobile]["name"]
            keyboard.append([
                InlineKeyboardButton(f"✅ Accept {name}", callback_data=f"accept_{req_mobile}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req_mobile}")
            ])
        await query.edit_message_text("➕ Friend Requests", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("send_req_"):
        sender_mobile = await get_user_mobile(query.from_user.id)
        target_mobile = data.split("_")[2]
        if target_mobile in users[sender_mobile]["pending"]:
            await query.edit_message_text("⏳ Request already sent!")
            return
        users[sender_mobile]["pending"].append(target_mobile)
        users[target_mobile]["requests"].append(sender_mobile)
        await save_to_channel(f"FRIEND_REQ|{sender_mobile}|{target_mobile}")
        await query.edit_message_text("✅ Friend Request Sent!")
    
    elif data.startswith("accept_"):
        accepter = await get_user_mobile(query.from_user.id)
        sender = data.split("_")[1]
        # Add both sides
        users[accepter]["friends"].append(sender)
        users[sender]["friends"].append(accepter)
        # Remove from pending/requests
        users[accepter]["requests"] = [r for r in users[accepter]["requests"] if r != sender]
        users[sender]["pending"] = [p for p in users[sender]["pending"] if p != accepter]
        await save_to_channel(f"FRIEND_ACCEPT|{sender}|{accepter}")
        await query.edit_message_text("✅ Friend Request Accepted!")

    elif data.startswith("chat_"):
        friend_mobile = data.split("_")[1]
        user_mobile = await get_user_mobile(query.from_user.id)
        chat_key = "_".join(sorted([user_mobile, friend_mobile]))
        await query.edit_message_text(
            f"💬 Chatting with {users[friend_mobile]['name']}\n\n"
            "Ab aap web app mein jaake photo + text bhej sakte hain!\n"
            f"Link: https://yourdomain.com/?chat={chat_key}"
        )

# ================= MESSAGE FROM CHANNEL (DATA STORAGE) =================
async def channel_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id == CHANNEL_ID:
        text = update.channel_post.text
        if not text:
            return
        
        # NEW USER
        if text.startswith("NEW_USER|"):
            _, mobile, name, password = text.split("|", 3)
            users[mobile] = {"name": name, "pass": password, "friends": [], "requests": [], "pending": []}
        
        # ADMIN MESSAGE TO USER
        elif text.startswith("ADMIN_MSG|"):
            _, mobile, message = text.split("|", 2)
            if mobile in users:
                await context.bot.send_message(int(mobile), f"📩 Admin Message:\n\n{message}")
        
        # FRIEND REQUEST
        elif text.startswith("FRIEND_REQ|"):
            _, sender, target = text.split("|")
            if target in users and sender not in users[target]["requests"]:
                users[target]["requests"].append(sender)
        
        # FRIEND ACCEPT
        elif text.startswith("FRIEND_ACCEPT|"):
            _, u1, u2 = text.split("|")
            if u1 in users and u2 in users:
                if u2 not in users[u1]["friends"]:
                    users[u1]["friends"].append(u2)
                if u1 not in users[u2]["friends"]:
                    users[u2]["friends"].append(u1)

# Helper
async def get_user_mobile(user_id):
    for mobile, data in users.items():
        if str(user_id) == mobile:  # temporary
            return mobile
    return None

async def save_to_channel(message):
    await application.bot.send_message(CHANNEL_ID, message)

# ================= MAIN =================
if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("users", admin_users))
    application.add_handler(CommandHandler("msg", admin_msg))
    application.add_handler(CommandHandler("changepass", change_pass))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.CHAT_TYPE.CHANNEL, channel_listener))
    
    print("Bot is running...")
    application.run_polling()

import telebot
from telebot import types
import os
import time

# =====================
# CONFIG
# =====================
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@EFOOTBALSTART"

MAIN_ADMIN = 7416577394
ADMINS = [8571600058, 6118062844]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =====================
# DATABASE
# =====================
sell_ads = []
buy_ads = []

user_state = {}
pending_post = {}
payment_time = {}

CARD_NUMBER = "9860 1001 2748 2345"
PRICE = 5000
TIME_LIMIT = 300


# =====================
# TEXT NORMALIZER (FIX BUTTONS)
# =====================
def t(msg):
    return msg.text.lower().strip() if msg and msg.text else ""


# =====================
# SUB CHECK
# =====================
def check_sub(user_id):
    try:
        member = bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# =====================
# START
# =====================
@bot.message_handler(commands=["start"])
def start(message):

    if not check_sub(message.from_user.id):

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📢 Kanal", url=f"https://t.me/{CHANNEL.replace('@','')}")
        )
        markup.add(
            types.InlineKeyboardButton("✅ Tekshirish", callback_data="check")
        )

        bot.send_message(message.chat.id, "❗ Kanalga obuna bo‘ling", reply_markup=markup)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("🔎 Qidirish", "📤 Sotish")
    markup.row("📥 Olish", "📂 Elonlar")
    markup.row("👨‍💼 Adminlar", "💰 Narxlar")
    markup.row("📚 Qoidalar")

    bot.send_message(message.chat.id, "🎮 <b>MARKET BOT</b>", reply_markup=markup)


# =====================
# SEARCH
# =====================
@bot.message_handler(func=lambda m: "qidir" in t(m))
def search(message):

    if not sell_ads:
        bot.send_message(message.chat.id, "❌ Elon yo‘q")
        return

    for ad in sell_ads:
        bot.send_message(message.chat.id, ad)


# =====================
# SELL START
# =====================
@bot.message_handler(func=lambda m: "sotish" in t(m))
def sell(message):

    user_state[message.from_user.id] = "photo"
    bot.send_message(message.chat.id, "📸 Rasm yuboring")


# =====================
# PHOTO HANDLER
# =====================
@bot.message_handler(content_types=["photo"])
def photo(message):

    uid = message.from_user.id

    if user_state.get(uid) != "photo":
        return

    pending_post[uid] = {
        "photo": message.photo[-1].file_id
    }

    user_state[uid] = "ask"

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Ha", callback_data=f"sell_yes_{uid}"),
        types.InlineKeyboardButton("❌ Yo‘q", callback_data=f"sell_no_{uid}")
    )

    bot.send_message(uid, "❓ Bu akkaunt sotiladimi?", reply_markup=markup)


# =====================
# BUY
# =====================
@bot.message_handler(func=lambda m: "olish" in t(m))
def buy(message):

    msg = bot.send_message(message.chat.id, "📥 Qanday akk kerak?")
    bot.register_next_step_handler(msg, save_buy)


def save_buy(message):

    buy_ads.append(message.text)

    bot.send_message(message.chat.id, "✅ Yuborildi")
    bot.send_message(MAIN_ADMIN, f"📥 BUY: {message.text}")


# =====================
# ELONLAR
# =====================
@bot.message_handler(func=lambda m: "elon" in t(m))
def ads(message):

    bot.send_message(
        message.chat.id,
        f"""📊 STATISTIKA

📤 Sotish: {len(sell_ads)}
📥 Olish: {len(buy_ads)}"""
    )


# =====================
# NARXLAR
# =====================
@bot.message_handler(func=lambda m: "narx" in t(m))
def prices(message):

    bot.send_message(message.chat.id, f"""💰 NARXLAR

📦 0 - 400K → 5000 so‘m
📦 400K - 1.4M → 6000 so‘m
📦 1.4M - 3M → 10000 so‘m
📦 3M+ → 15000 so‘m

💳 KARTA:
<code>{CARD_NUMBER}</code>

⏳ 5 daqiqa ichida to‘lov yuboring
""")


# =====================
# ADMINS
# =====================
@bot.message_handler(func=lambda m: "admin" in t(m))
def admins(message):

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("👑 Bosh Admin", url="https://t.me/EFUTBAL_STARTUVA10"),
        types.InlineKeyboardButton("👨‍💻 Admin 1", url="https://t.me/ERKINOV277"),
        types.InlineKeyboardButton("👨‍💻 Admin 2", url="https://t.me/doc_Marufjonov")
    )

    bot.send_message(message.chat.id, "👨‍💼 ADMINLAR", reply_markup=markup)


# =====================
# QOIDALAR
# =====================
@bot.message_handler(func=lambda m: "qoid" in t(m))
def rules(message):

    bot.send_message(message.chat.id, """📚 QOIDALAR

❗ Fake taqiqlanadi  
❗ Admin qarori yakuniy  
❗ To‘g‘ri ma’lumot kiriting
""")


# =====================
# CALLBACKS
# =====================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    if call.data == "check":

        if check_sub(call.from_user.id):
            bot.answer_callback_query(call.id, "OK")
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "Obuna bo‘ling")


    elif call.data.startswith("sell_yes_"):

        uid = int(call.data.split("_")[2])

        user_state[uid] = "clean"

        bot.send_message(uid, "❓ Akkaunt tozami?")


        if uid in pending_post:

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"ok_{uid}"),
                types.InlineKeyboardButton("❌ Bekor", callback_data=f"no_{uid}")
            )

            bot.send_photo(
                MAIN_ADMIN,
                pending_post[uid]["photo"],
                caption=f"📤 YANGI AKK\n👤 ID: {uid}",
                reply_markup=markup
            )


    elif call.data.startswith("sell_no_"):

        uid = int(call.data.split("_")[2])

        user_state.pop(uid, None)
        pending_post.pop(uid, None)

        bot.send_message(uid, "❌ Bekor qilindi")


    elif call.data.startswith("ok_"):

        uid = int(call.data.split("_")[1])

        bot.send_message(uid, "✅ Tasdiqlandi")

        if uid in pending_post:

            bot.send_photo(
                CHANNEL,
                pending_post[uid]["photo"],
                caption=f"🔥 YANGI AKK\n💰 {PRICE} so‘m\n👤 {uid}"
            )

            pending_post.pop(uid)


    elif call.data.startswith("no_"):

        uid = int(call.data.split("_")[1])

        bot.send_message(uid, "❌ Bekor qilindi")
        pending_post.pop(uid, None)


# =====================
# RUN
# =====================
print("Bot ishga tushdi...")
bot.infinity_polling(skip_pending=True)
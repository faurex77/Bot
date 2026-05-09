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
payment_time = {}
pending_post = {}

CARD_NUMBER = "9860 1001 2748 2345"
PRICE = 5000
TIME_LIMIT = 300


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
            types.InlineKeyboardButton(
                "📢 Kanalga obuna bo'lish",
                url=f"https://t.me/{CHANNEL.replace('@','')}"
            )
        )
        markup.add(
            types.InlineKeyboardButton("✅ Tekshirish", callback_data="check")
        )

        bot.send_message(
            message.chat.id,
            "❗ Botdan foydalanish uchun kanalga obuna bo'ling.",
            reply_markup=markup
        )
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("🔎 Akkount qidirish", "📤 Akk sotish")
    markup.row("📥 Akk olish", "📂 Elonlar")
    markup.row("👨‍💼 Adminlar", "💰 Narxlar")
    markup.row("📚 Qoidalar")

    bot.send_message(
        message.chat.id,
        "🎮 <b>EFOOTBALL MARKETPLACE</b>",
        reply_markup=markup
    )


# =====================
# SEARCH
# =====================
@bot.message_handler(func=lambda m: m.text and "Akkount qidirish" in m.text)
def search(message):

    if not sell_ads:
        bot.send_message(message.chat.id, "❌ Hozircha elon yo'q.")
        return

    for ad in sell_ads:
        bot.send_message(message.chat.id, ad)


# =====================
# SELL START
# =====================
@bot.message_handler(func=lambda m: m.text and "Akk sotish" in m.text)
def sell(message):

    user_state[message.from_user.id] = "photo"

    bot.send_message(message.chat.id, "📸 Akk rasm yuboring")


# =====================
# PHOTO
# =====================
@bot.message_handler(content_types=["photo"])
def photo_handler(message):

    uid = message.from_user.id

    if uid not in user_state:
        return

    if user_state[uid] == "photo":

        user_state[uid] = "ask_sell"

        pending_post[uid] = {
            "photo": message.photo[-1].file_id
        }

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Ha", callback_data=f"sell_yes_{uid}"),
            types.InlineKeyboardButton("❌ Yo‘q", callback_data=f"sell_no_{uid}")
        )

        bot.send_message(uid, "❓ Bu akkauntni sotasizmi?", reply_markup=markup)


# =====================
# BUY
# =====================
@bot.message_handler(func=lambda m: m.text and "Akk olish" in m.text)
def buy(message):

    msg = bot.send_message(message.chat.id, "📥 Qanday akk kerak?")

    bot.register_next_step_handler(msg, save_buy)


def save_buy(message):

    text = f"""📥 AKK OLAMAN

{message.text}

👤 @{message.from_user.username if message.from_user.username else "none"}"""

    buy_ads.append(text)

    bot.send_message(message.chat.id, "✅ Yuborildi")
    bot.send_message(MAIN_ADMIN, text)


# =====================
# ELONLAR
# =====================
@bot.message_handler(func=lambda m: m.text and "Elonlar" in m.text)
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
@bot.message_handler(func=lambda m: m.text and "Narxlar" in m.text)
def prices(message):

    bot.send_message(message.chat.id, f"""💰 NARXLAR

📦 0 - 400 000 → 5 000 so'm
📦 400 000 - 1.4M → 6 000 so'm
📦 1.4M - 3M → 10 000 so'm
📦 3M - 99M → 15 000 so'm

💳 KARTA:
<code>{CARD_NUMBER}</code>
""")


# =====================
# ADMINS
# =====================
@bot.message_handler(func=lambda m: m.text and "Adminlar" in m.text)
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
@bot.message_handler(func=lambda m: m.text and "Qoidalar" in m.text)
def rules(message):

    bot.send_message(message.chat.id, """📚 QOIDALAR

❗ Fake akk taqiqlanadi  
❗ Admin qarori yakuniy  
❗ To‘g‘ri ma'lumot kiriting
""")


# =====================
# CALLBACK
# =====================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    if call.data == "check":

        if check_sub(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ Tasdiqlandi")
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Obuna bo'ling")


    elif call.data.startswith("sell_yes_"):

        uid = int(call.data.split("_")[2])
        user_state[uid] = "clean"
        bot.send_message(uid, "❓ Akkaunt tozami?")


    elif call.data.startswith("sell_no_"):

        uid = int(call.data.split("_")[2])

        user_state.pop(uid, None)
        pending_post.pop(uid, None)

        bot.send_message(uid, "❌ Bekor qilindi")


    elif call.data.startswith("ok_"):

        uid = int(call.data.split("_")[1])

        bot.send_message(uid, "✅ Tasdiqlandi")

        if uid in pending_post:

            data = pending_post[uid]

            bot.send_photo(
                CHANNEL,
                data["photo"],
                caption=f"""🔥 YANGI AKK

💰 Narx: {PRICE} so'm

👤 ID: {uid}"""
            )

            pending_post.pop(uid)


    elif call.data.startswith("no_"):

        uid = int(call.data.split("_")[1])

        bot.send_message(uid, "❌ Bekor qilindi")

        if uid in pending_post:
            pending_post.pop(uid)


# =====================
# PAYMENT STEP
# =====================
@bot.message_handler(func=lambda m: True)
def text_handler(message):

    uid = message.from_user.id

    if uid not in user_state:
        return

    if user_state[uid] == "clean":

        user_state[uid] = "payment"
        payment_time[uid] = time.time()

        bot.send_message(
            uid,
            f"""💳 TO‘LOV

Narx: {PRICE} so'm

Karta:
<code>{CARD_NUMBER}</code>

⏳ 5 daqiqa ichida screenshot yuboring
"""
        )


@bot.message_handler(content_types=["photo"])
def payment_handler(message):

    uid = message.from_user.id

    if uid not in user_state:
        return

    if user_state[uid] != "payment":
        return

    if time.time() - payment_time.get(uid, 0) > TIME_LIMIT:
        bot.send_message(uid, "❌ Vaqt tugadi")
        user_state.pop(uid, None)
        return

    photo = message.photo[-1].file_id

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"ok_{uid}"),
        types.InlineKeyboardButton("❌ Bekor", callback_data=f"no_{uid}")
    )

    bot.send_photo(
        MAIN_ADMIN,
        photo,
        caption=f"💰 To‘lov\nUser: {uid}",
        reply_markup=markup
    )

    bot.send_message(uid, "⏳ Admin tekshiryapti...")


# =====================
# RUN
# =====================
print("Bot ishga tushdi...")
bot.infinity_polling(skip_pending=True)
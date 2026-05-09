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
# DATA
# =====================
state = {}
pending = {}
payment_time = {}

CARD_NUMBER = "9860 1001 2748 2345"
PRICE = 5000
TIME_LIMIT = 300


# =====================
# SUB CHECK
# =====================
def check_sub(user_id):
    try:
        m = bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
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
            types.InlineKeyboardButton("📢 Kanal", url=f"https://t.me/{CHANNEL.replace('@','')}"),
            types.InlineKeyboardButton("✅ Tekshirish", callback_data="check")
        )

        bot.send_message(message.chat.id, "❗ Kanalga obuna bo‘ling", reply_markup=markup)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("🔎 Qidirish", "📤 Sotish")
    markup.row("📥 Olish", "💰 Narxlar")
    markup.row("👨‍💼 Adminlar", "📚 Qoidalar")

    bot.send_message(message.chat.id, "🎮 <b>MARKET BOT</b>", reply_markup=markup)


# =====================
# SELL START
# =====================
@bot.message_handler(func=lambda m: "sotish" in (m.text or "").lower())
def sell(message):

    state[message.from_user.id] = "photo"
    bot.send_message(message.chat.id, "📸 Rasm yuboring")


# =====================
# BUY (SIMPLE)
# =====================
@bot.message_handler(func=lambda m: "olish" in (m.text or "").lower())
def buy(message):

    msg = bot.send_message(message.chat.id, "📥 Qanday akk kerak?")
    bot.register_next_step_handler(msg, save_buy)


def save_buy(message):

    bot.send_message(message.chat.id, "✅ Yuborildi")
    bot.send_message(MAIN_ADMIN, f"📥 BUY:\n{message.text}")


# =====================
# TEXT BUTTONS
# =====================
@bot.message_handler(func=lambda m: "narx" in (m.text or "").lower())
def prices(message):

    bot.send_message(message.chat.id, f"""💰 NARXLAR

📦 0 - 400K → 5000 so‘m
📦 400K - 1.4M → 6000 so‘m
📦 1.4M - 3M → 10000 so‘m
📦 3M+ → 15000 so‘m

💳 KARTA:
<code>{CARD_NUMBER}</code>
""")


@bot.message_handler(func=lambda m: "admin" in (m.text or "").lower())
def admins(message):

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("👑 Bosh Admin", url="https://t.me/EFUTBAL_STARTUVA10"),
        types.InlineKeyboardButton("👨‍💻 Admin 1", url="https://t.me/ERKINOV277"),
        types.InlineKeyboardButton("👨‍💻 Admin 2", url="https://t.me/doc_Marufjonov")
    )

    bot.send_message(message.chat.id, "👨‍💼 ADMINLAR", reply_markup=markup)


@bot.message_handler(func=lambda m: "qoid" in (m.text or "").lower())
def rules(message):

    bot.send_message(message.chat.id, """📚 QOIDALAR

❗ Fake taqiqlanadi  
❗ Admin qarori yakuniy  
❗ To‘g‘ri ma’lumot kiriting
""")


# =====================
# PHOTO ROUTER (🔥 ENG MUHIM FIX)
# =====================
@bot.message_handler(content_types=["photo"])
def photo_router(message):

    uid = message.from_user.id
    st = state.get(uid)

    # =====================
    # SELL FLOW
    # =====================
    if st == "photo":

        pending[uid] = {
            "photo": message.photo[-1].file_id
        }

        state[uid] = "ask"

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Ha", callback_data=f"yes_{uid}"),
            types.InlineKeyboardButton("❌ Yo‘q", callback_data=f"no_{uid}")
        )

        bot.send_message(uid, "❓ Akkaunt sotiladimi?", reply_markup=markup)


    # =====================
    # PAYMENT FLOW (ADMIN KO‘RADI)
    # =====================
    elif st == "payment":

        if time.time() - payment_time.get(uid, 0) > TIME_LIMIT:
            bot.send_message(uid, "❌ Vaqt tugadi")
            state.pop(uid, None)
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
            caption=f"💰 CHEK\nUser ID: {uid}",
            reply_markup=markup
        )

        bot.send_message(uid, "⏳ Admin tekshiryapti...")


# =====================
# CALLBACKS
# =====================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    uid = call.from_user.id

    if call.data == "check":
        if check_sub(uid):
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "Obuna bo‘ling")


    elif call.data.startswith("yes_"):

        uid2 = int(call.data.split("_")[1])

        state[uid2] = "clean"

        bot.send_message(uid2, "❓ Akkaunt tozami?")


    elif call.data.startswith("no_"):

        uid2 = int(call.data.split("_")[1])

        state.pop(uid2, None)
        pending.pop(uid2, None)

        bot.send_message(uid2, "❌ Bekor qilindi")


    elif call.data.startswith("ok_"):

        uid2 = int(call.data.split("_")[1])

        bot.send_message(uid2, "✅ Tasdiqlandi")

        if uid2 in pending:

            bot.send_photo(
                CHANNEL,
                pending[uid2]["photo"],
                caption=f"🔥 YANGI AKK\n💰 {PRICE} so‘m\n👤 {uid2}"
            )

            pending.pop(uid2, None)


    elif call.data.startswith("no_"):

        uid2 = int(call.data.split("_")[1])

        bot.send_message(uid2, "❌ Bekor")
        pending.pop(uid2, None)


# =====================
# CLEAN STEP
# =====================
@bot.message_handler(func=lambda m: state.get(m.from_user.id) == "clean")
def clean(message):

    uid = message.from_user.id

    state[uid] = "payment"
    payment_time[uid] = time.time()

    bot.send_message(
        uid,
        f"""💳 TO‘LOV

💰 {PRICE} so‘m

KARTA:
<code>{CARD_NUMBER}</code>

⏳ 5 daqiqa ichida screenshot yuboring
"""
    )


# =====================
# RUN
# =====================
print("BOT RUNNING...")
bot.infinity_polling(skip_pending=True)
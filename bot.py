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
sell_ads = []
buy_ads = []

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
    markup.row("📥 Olish", "📂 Elonlar")
    markup.row("👨‍💼 Adminlar", "💰 Narxlar")
    markup.row("📚 Qoidalar")

    bot.send_message(message.chat.id, "🎮 <b>MARKET BOT</b>", reply_markup=markup)


# =====================
# SELL START
# =====================
@bot.message_handler(func=lambda m: "sotish" in (m.text or "").lower())
def sell(message):

    state[message.from_user.id] = "photo"
    bot.send_message(message.chat.id, "📸 Rasm yuboring")


# =====================
# BUY
# =====================
@bot.message_handler(func=lambda m: "olish" in (m.text or "").lower())
def buy(message):

    msg = bot.send_message(message.chat.id, "📥 Qanday akk kerak?")
    bot.register_next_step_handler(msg, save_buy)


def save_buy(message):

    buy_ads.append(message.text)

    bot.send_message(message.chat.id, "✅ Yuborildi")
    bot.send_message(MAIN_ADMIN, f"📥 BUY:\n{message.text}")


# =====================
# PHOTO ROUTER (FIXED)
# =====================
@bot.message_handler(content_types=["photo"])
def photo_router(message):

    uid = message.from_user.id
    st = state.get(uid)

    # SELL PHOTO
    if st == "photo":

        pending[uid] = {
            "photo": message.photo[-1].file_id
        }

        state[uid] = "ask_sell"

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Ha", callback_data=f"yes_{uid}"),
            types.InlineKeyboardButton("Yo‘q", callback_data=f"no_{uid}")
        )

        bot.send_message(uid, "❓ Akkaunt sotiladimi?", reply_markup=markup)


    # PAYMENT CHECK (ADMIN KO‘RADIGAN QISM)
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
# CLEAN STEP (FIXED)
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
import telebot
from telebot import types
import os
import time

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL = "@EFOOTBALSTART"

MAIN_ADMIN = 7416577394
ADMINS = [8571600058, 6118062844]

CARD_NUMBER = "9860 1001 2748 2345"
TIME_LIMIT = 300

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# =========================
# DATABASE
# =========================
sell_ads = []
buy_ads = []

state = {}
pending = {}
payment_time = {}

# =========================
# SUB CHECK
# =========================
def check_sub(user_id):
    try:
        member = bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# =========================
# MAIN MENU
# =========================
def menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("🔎 Qidirish", "📤 Sotish")
    markup.row("📥 Olish", "📂 Elonlar")
    markup.row("👨‍💼 Adminlar", "💰 Narxlar")
    markup.row("📚 Qoidalar")

    return markup


# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):

    if not check_sub(message.from_user.id):

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "📢 Kanalga obuna bo‘lish",
                url=f"https://t.me/{CHANNEL.replace('@','')}"
            )
        )

        markup.add(
            types.InlineKeyboardButton(
                "✅ Tekshirish",
                callback_data="check"
            )
        )

        bot.send_message(
            message.chat.id,
            "❗ Botdan foydalanish uchun kanalga obuna bo‘ling",
            reply_markup=markup
        )
        return

    bot.send_message(
        message.chat.id,
        "🎮 <b>EFOOTBALL MARKETPLACE</b>",
        reply_markup=menu()
    )


# =========================
# SEARCH
# =========================
@bot.message_handler(func=lambda m: m.text == "🔎 Qidirish")
def search(message):

    if not sell_ads:
        bot.send_message(message.chat.id, "❌ Hozircha elon yo‘q")
        return

    last_ads = sell_ads[-3:]

    for ad in reversed(last_ads):
        bot.send_photo(
            message.chat.id,
            ad["photo"],
            caption=ad["caption"]
        )


# =========================
# SELL START
# =========================
@bot.message_handler(func=lambda m: m.text == "📤 Sotish")
def sell(message):

    state[message.from_user.id] = "photo"

    bot.send_message(
        message.chat.id,
        "📸 Akkaunt rasmini yuboring"
    )


# =========================
# BUY
# =========================
@bot.message_handler(func=lambda m: m.text == "📥 Olish")
def buy(message):

    msg = bot.send_message(
        message.chat.id,
        "📥 Qanday akkaunt kerak?"
    )

    bot.register_next_step_handler(msg, save_buy)


def save_buy(message):

    username = message.from_user.username

    text = f"""
📥 <b>AKKAUNT OLAMAN</b>

{message.text}

👤 @{username if username else "none"}
"""

    buy_ads.append(text)

    bot.send_message(message.chat.id, "✅ Yuborildi")
    bot.send_message(MAIN_ADMIN, text)


# =========================
# ELONLAR
# =========================
@bot.message_handler(func=lambda m: m.text == "📂 Elonlar")
def ads(message):

    uid = message.from_user.id

    user_sell = 0

    for ad in sell_ads:
        if ad["owner"] == uid:
            user_sell += 1

    bot.send_message(
        message.chat.id,
        f"""
📊 <b>SIZNING STATISTIKANGIZ</b>

📤 Siz bergan sotuv elonlari: {user_sell}
📥 Olish elonlari: {len(buy_ads)}
"""
    )


# =========================
# NARXLAR
# =========================
@bot.message_handler(func=lambda m: m.text == "💰 Narxlar")
def prices(message):

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "📢 Kanal",
            url="https://t.me/EFOOTBALSTART"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👑 Bosh Admin",
            url="https://t.me/EFUTBAL_STARTUVA10"
        )
    )

    bot.send_message(
        message.chat.id,
        """
💰 <b>NARXLAR</b>

📌 Narxlarni kanal orqali ko‘rishingiz mumkin.
📩 Yoki bosh admin bilan bog‘laning.
""",
        reply_markup=markup
    )


# =========================
# ADMINS
# =========================
@bot.message_handler(func=lambda m: m.text == "👨‍💼 Adminlar")
def admins(message):

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "👑 Bosh Admin",
            url="https://t.me/EFUTBAL_STARTUVA10"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👨‍💻 Admin 1",
            url="https://t.me/ERKINOV277"
        )
    )

    markup.add(
        types.InlineKeyboardButton(
            "👨‍💻 Admin 2",
            url="https://t.me/doc_Marufjonov"
        )
    )

    bot.send_message(
        message.chat.id,
        "👨‍💼 ADMINLAR",
        reply_markup=markup
    )


# =========================
# RULES
# =========================
@bot.message_handler(func=lambda m: m.text == "📚 Qoidalar")
def rules(message):

    bot.send_message(
        message.chat.id,
        """
📚 <b>QOIDALAR</b>

❗ Fake akkaunt taqiqlanadi
❗ Admin qarori yakuniy
❗ To‘g‘ri ma’lumot kiriting
❗ Chek fake bo‘lsa ban
"""
    )


# =========================
# PHOTO ROUTER
# =========================
@bot.message_handler(content_types=["photo"])
def photo_router(message):

    uid = message.from_user.id
    st = state.get(uid)

    # =====================
    # SELL PHOTO
    # =====================
    if st == "photo":

        pending[uid] = {
            "photo": message.photo[-1].file_id,
            "username": message.from_user.username
        }

        state[uid] = "price"

        bot.send_message(
            uid,
            "💰 Akkaunt narxini kiriting\n\nMasalan: 50000"
        )

    # =====================
    # PAYMENT CHECK
    # =====================
    elif st == "payment":

        if time.time() - payment_time.get(uid, 0) > TIME_LIMIT:

            bot.send_message(uid, "❌ Vaqt tugadi")

            state.pop(uid, None)
            pending.pop(uid, None)

            return

        photo = message.photo[-1].file_id

        markup = types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton(
                "✅ Tasdiqlash",
                callback_data=f"ok_{uid}"
            ),
            types.InlineKeyboardButton(
                "❌ Bekor",
                callback_data=f"cancel_{uid}"
            )
        )

        bot.send_photo(
            MAIN_ADMIN,
            photo,
            caption=f"💰 TO‘LOV CHEKI\n\n👤 User ID: {uid}",
            reply_markup=markup
        )

        bot.send_message(
            uid,
            "⏳ Admin chekni tekshiryapti..."
        )


# =========================
# PRICE INPUT
# =========================
@bot.message_handler(func=lambda m: state.get(m.from_user.id) == "price")
def get_price(message):

    uid = message.from_user.id
    text = message.text.strip()

    if not text.isdigit():

        bot.send_message(
            uid,
            "❌ Faqat son kiriting\n\nMasalan: 50000"
        )

        return

    pending[uid]["price"] = text

    state[uid] = "clean"

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    markup.row("Ha", "Yo‘q")

    bot.send_message(
        uid,
        "❓ Akkaunt tozami?",
        reply_markup=markup
    )


# =========================
# CLEAN STEP
# =========================
@bot.message_handler(func=lambda m: state.get(m.from_user.id) == "clean")
def clean(message):

    uid = message.from_user.id

    answer = message.text.lower()

    if answer not in ["ha", "yo‘q", "yo'q"]:

        bot.send_message(uid, "❌ Ha yoki Yo‘q yozing")
        return

    pending[uid]["clean"] = answer

    state[uid] = "payment"

    payment_time[uid] = time.time()

    bot.send_message(
        uid,
        f"""
💳 <b>TO‘LOV</b>

💰 5000 so‘m

💳 KARTA:
<code>{CARD_NUMBER}</code>

⏳ 5 daqiqa ichida chek screenshot yuboring
""",
        reply_markup=menu()
    )


# =========================
# CALLBACKS
# =========================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    uid = call.from_user.id

    # =====================
    # CHECK SUB
    # =====================
    if call.data == "check":

        if check_sub(uid):

            bot.answer_callback_query(call.id, "✅ Tasdiqlandi")

            start(call.message)

        else:

            bot.answer_callback_query(
                call.id,
                "❌ Kanalga obuna bo‘ling"
            )

    # =====================
    # ADMIN APPROVE
    # =====================
    elif call.data.startswith("ok_"):

        uid2 = int(call.data.split("_")[1])

        if uid2 not in pending:
            return

        username = pending[uid2].get("username")

        if username:
            seller = f"@{username}"
        else:
            seller = f'<a href="tg://user?id={uid2}">User</a>'

        caption = f"""
🔥 <b>YANGI AKKAUNT</b>

💰 Narx: {pending[uid2]['price']} so‘m
🧹 Tozaligi: {pending[uid2]['clean']}

👤 Sotuvchi: {seller}
"""

        bot.send_photo(
            CHANNEL,
            pending[uid2]["photo"],
            caption=caption
        )

        sell_ads.append({
            "photo": pending[uid2]["photo"],
            "caption": caption,
            "owner": uid2
        })

        bot.send_message(
            uid2,
            "✅ Eloningiz tasdiqlandi va kanalga joylandi",
            reply_markup=menu()
        )

        state.pop(uid2, None)
        pending.pop(uid2, None)

    # =====================
    # ADMIN CANCEL
    # =====================
    elif call.data.startswith("cancel_"):

        uid2 = int(call.data.split("_")[1])

        bot.send_message(
            uid2,
            "❌ Eloningiz bekor qilindi",
            reply_markup=menu()
        )

        state.pop(uid2, None)
        pending.pop(uid2, None)


# =========================
# UNKNOWN TEXT
# =========================
@bot.message_handler(func=lambda m: True)
def unknown(message):

    bot.send_message(
        message.chat.id,
        "❌ Tugmalardan foydalaning",
        reply_markup=menu()
    )


# =========================
# RUN
# =========================
print("BOT ISHGA TUSHDI...")
bot.infinity_polling(skip_pending=True)
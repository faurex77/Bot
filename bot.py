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
            types.InlineKeyboardButton("📢 Kanal", url=f"https://t.me/{CHANNEL.replace('@','')}"),
            types.InlineKeyboardButton("✅ Tekshirish", callback_data="check")
        )

        bot.send_message(message.chat.id, "❗ Obuna bo‘ling", reply_markup=markup)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("🔎 Qidirish", "📤 Sotish")
    markup.row("📥 Olish", "📂 Elonlar")
    markup.row("👨‍💼 Adminlar", "💰 Narxlar")
    markup.row("⚙ Admin Panel", "📚 Qoidalar")

    bot.send_message(message.chat.id, "🎮 MARKET BOT", reply_markup=markup)


# =====================
# SEARCH
# =====================
@bot.message_handler(func=lambda m: m.text and "Qidirish" in m.text)
def search(message):

    for ad in sell_ads:
        bot.send_message(message.chat.id, ad)


# =====================
# SELL
# =====================
@bot.message_handler(func=lambda m: m.text and "Sotish" in m.text)
def sell(message):

    user_state[message.from_user.id] = "photo"
    bot.send_message(message.chat.id, "📸 Rasm yuboring")


# =====================
# PHOTO
# =====================
@bot.message_handler(content_types=["photo"])
def photo(message):

    uid = message.from_user.id

    if user_state.get(uid) != "photo":
        return

    pending_post[uid] = {
        "photo": message.photo[-1].file_id
    }

    user_state[uid] = "confirm_sell"

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Ha", callback_data=f"sell_yes_{uid}"),
        types.InlineKeyboardButton("Yo‘q", callback_data=f"sell_no_{uid}")
    )

    bot.send_message(uid, "Sotasizmi?", reply_markup=markup)


# =====================
# ADMIN PANEL
# =====================
@bot.message_handler(func=lambda m: m.text and "Admin Panel" in m.text)
def admin_panel(message):

    if message.from_user.id != MAIN_ADMIN and message.from_user.id not in ADMINS:
        bot.send_message(message.chat.id, "❌ Ruxsat yo‘q")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)

    markup.add(
        types.InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
        types.InlineKeyboardButton("📤 Yangi sotuvlar", callback_data="admin_sells"),
        types.InlineKeyboardButton("📥 Yangi olishlar", callback_data="admin_buys"),
        types.InlineKeyboardButton("🔄 Bot holati", callback_data="admin_status")
    )

    bot.send_message(message.chat.id, "⚙ ADMIN PANEL", reply_markup=markup)


# =====================
# CALLBACKS
# =====================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    uid = call.from_user.id

    # SUB CHECK
    if call.data == "check":
        if check_sub(uid):
            bot.answer_callback_query(call.id, "OK")
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "Obuna bo‘ling")


    # SELL YES
    elif call.data.startswith("sell_yes_"):

        uid2 = int(call.data.split("_")[2])

        user_state[uid2] = "payment"

        bot.send_message(uid2, f"""💳 TO‘LOV

💰 {PRICE} so‘m

Karta:
<code>{CARD_NUMBER}</code>""")


        # ADMINGA YUBORISH
        if uid2 in pending_post:

            bot.send_photo(
                MAIN_ADMIN,
                pending_post[uid2]["photo"],
                caption=f"📤 YANGI AKK\nID: {uid2}",
                reply_markup=admin_buttons(uid2)
            )


    # SELL NO
    elif call.data.startswith("sell_no_"):

        uid2 = int(call.data.split("_")[2])
        pending_post.pop(uid2, None)
        user_state.pop(uid2, None)

        bot.send_message(uid2, "❌ Bekor")


    # ADMIN OK
    elif call.data.startswith("ok_"):

        uid2 = int(call.data.split("_")[1])

        bot.send_message(uid2, "✅ Tasdiqlandi")

        if uid2 in pending_post:

            bot.send_photo(
                CHANNEL,
                pending_post[uid2]["photo"],
                caption=f"🔥 YANGI AKK\n💰 {PRICE} so‘m\n👤 {uid2}"
            )

            pending_post.pop(uid2)


    # ADMIN NO
    elif call.data.startswith("no_"):

        uid2 = int(call.data.split("_")[1])

        bot.send_message(uid2, "❌ Bekor qilindi")
        pending_post.pop(uid2, None)


    # =====================
    # ADMIN PANEL CALLBACKS
    # =====================
    elif call.data == "admin_stats":

        bot.send_message(
            uid,
            f"""📊 STATISTIKA

📤 Sotuv: {len(sell_ads)}
📥 Olish: {len(buy_ads)}"""
        )


    elif call.data == "admin_sells":

        bot.send_message(uid, "📤 So‘nggi sotuvlar:")

        for i in sell_ads[-5:]:
            bot.send_message(uid, i)


    elif call.data == "admin_buys":

        bot.send_message(uid, "📥 So‘nggi olishlar:")

        for i in buy_ads[-5:]:
            bot.send_message(uid, i)


    elif call.data == "admin_status":

        bot.send_message(uid, "🟢 Bot ishlayapti")


# =====================
# HELPERS
# =====================
def admin_buttons(uid):

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton("✅ Tasdiq", callback_data=f"ok_{uid}"),
        types.InlineKeyboardButton("❌ Bekor", callback_data=f"no_{uid}")
    )

    return markup


# =====================
# BUY
# =====================
@bot.message_handler(func=lambda m: m.text and "Olish" in m.text)
def buy(message):

    msg = bot.send_message(message.chat.id, "Qanday akk kerak?")

    bot.register_next_step_handler(msg, save_buy)


def save_buy(message):

    buy_ads.append(message.text)

    bot.send_message(message.chat.id, "Yuborildi")


# =====================
# RUN
# =====================
print("Bot RUN + Admin Panel")
bot.infinity_polling(skip_pending=True)
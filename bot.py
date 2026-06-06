#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telebot
from telebot import types
import json
import os
import time
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "BU_YERGA_TOKENNI_KIR")
ADMIN_IDS = [7416577394]

SOTISH_ADMIN_ID = 7416577394
KANAL = "@EFOOTBALSTART"
KANAL_ID = "@EFOOTBALSTART"

KARTA_RAQAM = "9860 1001 2748 2345"
KARTA_EGASI = "UVAYSIDDIN VAFOEV"
TOLOV_SUMMA = 5000

ADMINS_LIST = {
    "@EFUTBAL_STARTUVA10": "Bosh admin",
    "@Fuzzsss": "Bot yaratuvchisi",
}

PRICES = (
    "🛍 Akkauntlarga e'lon berish narxlari:\n\n"
    "💵 0 dan 500 000 gacha — 4 000 so'm\n"
    "💵 500 000 dan 1 000 000 gacha — 6 000 so'm\n"
    "💵 1 000 000 dan 5 000 000 gacha — 10 000 so'm\n"
    "💵 5 000 000 dan 20 000 000 gacha — 15 000 so'm\n\n"
    "♻️ Botda avto to'lov qilish imkoniyati mavjud!\n\n"
    "❗ Akkount olaman deb reklama berishingiz ham mumkin!"
)

QOIDALAR = (
    "📚 Qoidalar:\n\n"
    "1️⃣ Har bir foydalanuvchi savdo oldidan akkountni tekshirsin.\n"
    "2️⃣ Spam va soxta e'lonlar taqiqlanadi.\n"
    "3️⃣ Qoidabuzarlarga cheklov qo'yiladi.\n"
    "4️⃣ Firibgarlik uchun bot javobgar emas.\n\n"
    "👨‍💻 Bot yaratuvchisi: @Fuzzsss\n"
    "📢 Kanal: @EFOOTBALSTART\n"
    "👨‍💼 Admin: @EFUTBAL_STARTUVA10\n"
    "💳 Karta: 9860 1001 2748 2345\n"
    "👤 Karta egasi: UVAYSIDDIN VAFOEV"
)

DB_FILE = "baza.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"elonlar": [], "users": {}, "kutish": {}}

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def next_id():
    db = load_db()
    elonlar = db.get("elonlar", [])
    if not elonlar:
        return 1
    return max(e["id"] for e in elonlar) + 1

bot = telebot.TeleBot(BOT_TOKEN)
states = {}
udata = {}

def check_sub(uid):
    try:
        m = bot.get_chat_member(KANAL, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("🔍 Akkount qidirish"),
        types.KeyboardButton("➕ E'lon berish"),
        types.KeyboardButton("📋 E'lonlarim"),
        types.KeyboardButton("👨‍💼 Adminlar"),
        types.KeyboardButton("📚 Qoidalar"),
        types.KeyboardButton("💰 E'lon narxlari"),
    )
    return kb

def tur_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("💵 Sotish e'loni"),
        types.KeyboardButton("🔎 Olish e'loni"),
        types.KeyboardButton("🔙 Orqaga"),
    )
    return kb

def ha_yoq_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton("✅ Ha"), types.KeyboardButton("❌ Yo'q"))
    return kb

def obmen_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton("♻️ Obmen ko'raman"), types.KeyboardButton("❌ Obmen yo'q"))
    return kb

def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Bekor qilish"))
    return kb

def format_sotish(e):
    google_val = "✅ Ha" if e.get("google") else "❌ Yo'q"
    obmen_val = "♻️ Ko'raman" if e.get("obmen") else "❌ Yo'q"
    text = (
        "🏪 SOTISH E'LONI\n"
        "━━━━━━━━━━━━━━━\n"
        "🆔 E'lon: #" + str(e["id"]) + "\n"
        "💰 Narx: " + str(e.get("narx", 0)) + " so'm\n"
        "🔐 Google: " + google_val + "\n"
        "♻️ Obmen: " + obmen_val + "\n"
    )
    izoh = e.get("izoh", "")
    if izoh:
        text += "📝 Izoh: " + izoh + "\n"
    text += (
        "━━━━━━━━━━━━━━━\n"
        "👤 Muallif: @" + str(e.get("username", "noma'lum")) + "\n"
        "📅 Sana: " + e.get("sana", "") + "\n"
        "━━━━━━━━━━━━━━━"
    )
    return text

def format_olish(e):
    google_val = "✅ Ha" if e.get("google") else "❌ Yo'q"
    text = (
        "🔎 OLISH E'LONI\n"
        "━━━━━━━━━━━━━━━\n"
        "🆔 E'lon: #" + str(e["id"]) + "\n"
        "💵 Byudjet: " + str(e.get("byudjet", 0)) + " so'm\n"
        "🔐 Google kerak: " + google_val + "\n"
    )
    tavsif = e.get("tavsif", "")
    if tavsif:
        text += "📝 Tavsif: " + tavsif + "\n"
    text += (
        "━━━━━━━━━━━━━━━\n"
        "👤 Muallif: @" + str(e.get("username", "noma'lum")) + "\n"
        "📅 Sana: " + e.get("sana", "") + "\n"
        "━━━━━━━━━━━━━━━"
    )
    return text

def format_elon(e):
    if e["tur"] == "sotish":
        return format_sotish(e)
    return format_olish(e)

def tolov_xabari(uid):
    text = (
        "💳 To'lov ma'lumotlari:\n\n"
        "💰 Summa: " + str(TOLOV_SUMMA) + " so'm\n"
        "💳 Karta: " + KARTA_RAQAM + "\n"
        "👤 Karta egasi: " + KARTA_EGASI + "\n\n"
        "✅ To'lovni amalga oshirib, chek rasmini yuboring!\n"
        "⏳ Admin tasdiqlashidan so'ng e'lon joylashtiriladi."
    )
    return text

@bot.message_handler(commands=["start"])
def start_cmd(msg):
    uid = msg.from_user.id
    if not check_sub(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Kanalga obuna", url="https://t.me/EFOOTBALSTART"))
        kb.add(types.InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub"))
        bot.send_message(
            msg.chat.id,
            "🚀 Botdan foydalanish uchun kanalga obuna bo'ling:\n\n📢 @EFOOTBALSTART",
            reply_markup=kb
        )
        return
    db = load_db()
    uid_str = str(uid)
    if "users" not in db:
        db["users"] = {}
    if uid_str not in db["users"]:
        db["users"][uid_str] = {
            "id": uid,
            "username": msg.from_user.username,
            "sana": datetime.now().strftime("%d.%m.%Y")
        }
        save_db(db)
    states[uid] = "main"
    bot.send_message(
        msg.chat.id,
        "👋 Salom " + msg.from_user.first_name + "!\n\n"
        "🏪 EFUZPAGESHOP botiga xush kelibsiz!\n"
        "⚽ eFootball akkountlarini sotish va sotib olish platformasi.",
        reply_markup=main_kb()
    )

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_sub_cb(call):
    uid = call.from_user.id
    if check_sub(uid):
        bot.answer_callback_query(call.id, "Tasdiqlandi!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        states[uid] = "main"
        bot.send_message(
            call.message.chat.id,
            "✅ Xush kelibsiz " + call.from_user.first_name + "!",
            reply_markup=main_kb()
        )
    else:
        bot.answer_callback_query(call.id, "Siz hali obuna bo'lmadingiz!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "📚 Qoidalar")
def qoidalar_h(msg):
    bot.send_message(msg.chat.id, QOIDALAR, reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "💰 E'lon narxlari")
def narxlar_h(msg):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✉️ Bot egasi", url="https://t.me/EFUTBAL_STARTUVA10"))
    bot.send_message(msg.chat.id, PRICES, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "👨‍💼 Adminlar")
def adminlar_h(msg):
    kb = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for uname in ADMINS_LIST:
        clean = uname.replace("@", "")
        btns.append(types.InlineKeyboardButton("👤 " + uname, url="https://t.me/" + clean))
    kb.add(*btns)
    bot.send_message(msg.chat.id, "👨‍💼 Adminlar ro'yxati:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📋 E'lonlarim")
def elonlarim_h(msg):
    uid = msg.from_user.id
    db = load_db()
    my = [e for e in db.get("elonlar", []) if e["user_id"] == uid and e["faol"]]
    if not my:
        bot.send_message(msg.chat.id, "🙅 Sizda aktiv e'lon topilmadi!", reply_markup=main_kb())
        return
    bot.send_message(msg.chat.id, "📋 Sizning faol e'lonlaringiz:")
    for e in my:
        text = format_elon(e)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑 O'chirish", callback_data="del_" + str(e["id"])))
        if e.get("rasm"):
            bot.send_photo(msg.chat.id, e["rasm"], caption=text, reply_markup=kb)
        else:
            bot.send_message(msg.chat.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_") and not c.data.startswith("del_a_"))
def del_elon_cb(call):
    eid = int(call.data.replace("del_", ""))
    db = load_db()
    for e in db["elonlar"]:
        if e["id"] == eid and e["user_id"] == call.from_user.id:
            e["faol"] = False
            save_db(db)
            bot.answer_callback_query(call.id, "E'lon o'chirildi.")
            bot.send_message(call.message.chat.id, "✅ E'lon #" + str(eid) + " o'chirildi.", reply_markup=main_kb())
            return
    bot.answer_callback_query(call.id, "Topilmadi.")

@bot.message_handler(func=lambda m: m.text == "🔍 Akkount qidirish")
def qidiruv_h(msg):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💵 Sotish e'lonlari", callback_data="search_sotish"),
        types.InlineKeyboardButton("🔎 Olish e'lonlari", callback_data="search_olish"),
    )
    bot.send_message(msg.chat.id, "🔍 Qaysi turdagi e'lonlarni ko'rmoqchisiz?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["search_sotish", "search_olish"])
def search_cb(call):
    tur = "sotish" if call.data == "search_sotish" else "olish"
    db = load_db()
    elonlar = [e for e in db.get("elonlar", []) if e["tur"] == tur and e["faol"]]
    if not elonlar:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "😔 Hozircha bu turdagi e'lon yo'q.", reply_markup=main_kb())
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📋 " + str(len(elonlar)) + " ta e'lon topildi:")
    for e in elonlar[-10:]:
        text = format_elon(e)
        kb = types.InlineKeyboardMarkup()
        uname = e.get("username", "")
        if uname and uname != "noma'lum":
            kb.add(types.InlineKeyboardButton("💬 Bog'lanish", url="https://t.me/" + uname))
        if e.get("rasm"):
            bot.send_photo(call.message.chat.id, e["rasm"], caption=text, reply_markup=kb)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ E'lon berish")
def elon_berish_h(msg):
    uid = msg.from_user.id
    if not check_sub(uid):
        bot.send_message(msg.chat.id, "❌ Avval kanalga obuna bo'ling!", reply_markup=main_kb())
        return
    states[uid] = "elon_tur"
    udata[uid] = {}
    bot.send_message(msg.chat.id, "📝 Qanday e'lon berishni xohlaysiz?", reply_markup=tur_kb())

@bot.message_handler(func=lambda m: m.text == "💵 Sotish e'loni" and states.get(m.from_user.id) == "elon_tur")
def sotish_start(msg):
    uid = msg.from_user.id
    states[uid] = "sotish_rasm"
    udata[uid]["tur"] = "sotish"
    bot.send_message(msg.chat.id, "🖼 Akkount asosiy tarkib rasmini yuboring:", reply_markup=cancel_kb())

@bot.message_handler(content_types=["photo"], func=lambda m: states.get(m.from_user.id) == "sotish_rasm")
def sotish_rasm_h(msg):
    uid = msg.from_user.id
    udata[uid]["rasm"] = msg.photo[-1].file_id
    states[uid] = "sotish_google"
    bot.send_message(msg.chat.id, "🔐 Akkountda Google yoki Game Center ulanganmi?", reply_markup=ha_yoq_kb())

@bot.message_handler(func=lambda m: m.text in ["✅ Ha", "❌ Yo'q"] and states.get(m.from_user.id) == "sotish_google")
def sotish_google_h(msg):
    uid = msg.from_user.id
    udata[uid]["google"] = msg.text == "✅ Ha"
    states[uid] = "sotish_obmen"
    bot.send_message(msg.chat.id, "♻️ Obmen ko'rasizmi?", reply_markup=obmen_kb())

@bot.message_handler(func=lambda m: m.text in ["♻️ Obmen ko'raman", "❌ Obmen yo'q"] and states.get(m.from_user.id) == "sotish_obmen")
def sotish_obmen_h(msg):
    uid = msg.from_user.id
    udata[uid]["obmen"] = msg.text == "♻️ Obmen ko'raman"
    states[uid] = "sotish_narx"
    bot.send_message(msg.chat.id, "💰 Akkount narxini kiriting (faqat raqam):\nMisol: 500000", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: states.get(m.from_user.id) == "sotish_narx")
def sotish_narx_h(msg):
    uid = msg.from_user.id
    if msg.text == "❌ Bekor qilish":
        cancel_h(msg)
        return
    try:
        narx = int(msg.text.replace(" ", "").replace(",", ""))
        udata[uid]["narx"] = narx
        states[uid] = "sotish_izoh"
        bot.send_message(msg.chat.id, "📝 Qo'shimcha ma'lumot kiriting.\nYo'q deb yozsangiz o'tkazib yuboradi:", reply_markup=cancel_kb())
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Faqat raqam kiriting! Masalan: 500000")

@bot.message_handler(func=lambda m: states.get(m.from_user.id) == "sotish_izoh")
def sotish_izoh_h(msg):
    uid = msg.from_user.id
    if msg.text == "❌ Bekor qilish":
        cancel_h(msg)
        return
    udata[uid]["izoh"] = "" if msg.text.lower() == "yo'q" else msg.text
    states[uid] = "tolov_kutish"
    bot.send_message(msg.chat.id, tolov_xabari(uid), reply_markup=cancel_kb())
    bot.send_message(msg.chat.id, "📸 Chek rasmini yuboring:")

@bot.message_handler(func=lambda m: m.text == "🔎 Olish e'loni" and states.get(m.from_user.id) == "elon_tur")
def olish_start(msg):
    uid = msg.from_user.id
    states[uid] = "olish_byudjet"
    udata[uid]["tur"] = "olish"
    bot.send_message(msg.chat.id, "💵 Byudjetingizni kiriting (so'm):\nMisol: 1000000", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: states.get(m.from_user.id) == "olish_byudjet")
def olish_byudjet_h(msg):
    uid = msg.from_user.id
    if msg.text == "❌ Bekor qilish":
        cancel_h(msg)
        return
    try:
        b = int(msg.text.replace(" ", "").replace(",", ""))
        udata[uid]["byudjet"] = b
        states[uid] = "olish_google"
        bot.send_message(msg.chat.id, "🔐 Google yoki Game Center kerakmi?", reply_markup=ha_yoq_kb())
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Faqat raqam kiriting! Masalan: 1000000")

@bot.message_handler(func=lambda m: m.text in ["✅ Ha", "❌ Yo'q"] and states.get(m.from_user.id) == "olish_google")
def olish_google_h(msg):
    uid = msg.from_user.id
    udata[uid]["google"] = msg.text == "✅ Ha"
    states[uid] = "olish_tavsif"
    bot.send_message(msg.chat.id, "📝 Qanday akkount kerakligini yozing:", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: states.get(m.from_user.id) == "olish_tavsif")
def olish_tavsif_h(msg):
    uid = msg.from_user.id
    if msg.text == "❌ Bekor qilish":
        cancel_h(msg)
        return
    udata[uid]["tavsif"] = msg.text
    states[uid] = "tolov_kutish"
    bot.send_message(msg.chat.id, tolov_xabari(uid), reply_markup=cancel_kb())
    bot.send_message(msg.chat.id, "📸 Chek rasmini yuboring:")

@bot.message_handler(content_types=["photo"], func=lambda m: states.get(m.from_user.id) == "tolov_kutish")
def chek_rasm_h(msg):
    uid = msg.from_user.id
    chek_file_id = msg.photo[-1].file_id
    db = load_db()
    if "kutish" not in db:
        db["kutish"] = {}
    db["kutish"][str(uid)] = {
        "user_id": uid,
        "username": msg.from_user.username if msg.from_user.username else "noma'lum",
        "ism": msg.from_user.first_name,
        "elon_data": udata[uid].copy(),
        "chek": chek_file_id,
        "sana": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_db(db)
    states[uid] = "main"
    bot.send_message(
        msg.chat.id,
        "✅ Chek qabul qilindi!\n"
        "⏳ Admin tekshirgandan so'ng e'lon joylashtiriladi.\n"
        "Odatda 5-30 daqiqa ichida tasdiqlanadi.",
        reply_markup=main_kb()
    )
    uname = msg.from_user.username if msg.from_user.username else "noma'lum"
    elon_turi = udata[uid].get("tur", "")
    if elon_turi == "sotish":
        narx = udata[uid].get("narx", 0)
        admin_text = (
            "💳 YANGI TO'LOV CHEKI\n"
            "━━━━━━━━━━━━━━━\n"
            "👤 Foydalanuvchi: @" + uname + "\n"
            "📋 E'lon turi: Sotish\n"
            "💰 Akkount narxi: " + str(narx) + " so'm\n"
            "💳 To'lov: " + str(TOLOV_SUMMA) + " so'm\n"
            "📅 Sana: " + datetime.now().strftime("%d.%m.%Y %H:%M") + "\n"
            "━━━━━━━━━━━━━━━"
        )
    else:
        byudjet = udata[uid].get("byudjet", 0)
        admin_text = (
            "💳 YANGI TO'LOV CHEKI\n"
            "━━━━━━━━━━━━━━━\n"
            "👤 Foydalanuvchi: @" + uname + "\n"
            "📋 E'lon turi: Olish\n"
            "💵 Byudjet: " + str(byudjet) + " so'm\n"
            "💳 To'lov: " + str(TOLOV_SUMMA) + " so'm\n"
            "📅 Sana: " + datetime.now().strftime("%d.%m.%Y %H:%M") + "\n"
            "━━━━━━━━━━━━━━━"
        )
    admin_kb = types.InlineKeyboardMarkup(row_width=2)
    admin_kb.add(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data="tasdiq_" + str(uid)),
        types.InlineKeyboardButton("❌ Rad etish", callback_data="rad_" + str(uid)),
    )
    for aid in ADMIN_IDS:
        try:
            bot.send_photo(aid, chek_file_id, caption=admin_text, reply_markup=admin_kb)
        except:
            pass
    udata[uid] = {}

@bot.callback_query_handler(func=lambda c: c.data.startswith("tasdiq_"))
def tasdiq_cb(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    uid = int(call.data.replace("tasdiq_", ""))
    db = load_db()
    kutish = db.get("kutish", {})
    if str(uid) not in kutish:
        bot.answer_callback_query(call.id, "Ma'lumot topilmadi!")
        return
    malumot = kutish[str(uid)]
    elon_data = malumot["elon_data"]
    eid = next_id()
    elon = {
        "id": eid,
        "user_id": uid,
        "username": malumot.get("username", "noma'lum"),
        "ism": malumot.get("ism", ""),
        "tur": elon_data.get("tur"),
        "faol": True,
        "sana": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    if elon["tur"] == "sotish":
        elon["rasm"] = elon_data.get("rasm")
        elon["google"] = elon_data.get("google", False)
        elon["obmen"] = elon_data.get("obmen", False)
        elon["narx"] = elon_data.get("narx", 0)
        elon["izoh"] = elon_data.get("izoh", "")
    else:
        elon["byudjet"] = elon_data.get("byudjet", 0)
        elon["google"] = elon_data.get("google", False)
        elon["tavsif"] = elon_data.get("tavsif", "")
    if "elonlar" not in db:
        db["elonlar"] = []
    db["elonlar"].append(elon)
    del db["kutish"][str(uid)]
    save_db(db)
    bot.answer_callback_query(call.id, "E'lon tasdiqlandi!")
    bot.edit_message_caption(
        caption=call.message.caption + "\n\n✅ TASDIQLANDI",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    uname = elon.get("username", "")
    text = format_elon(elon)
    try:
        kb = types.InlineKeyboardMarkup()
        if uname and uname != "noma'lum":
            kb.add(types.InlineKeyboardButton("💬 Bog'lanish", url="https://t.me/" + uname))
        if elon["tur"] == "sotish":
            if elon.get("rasm"):
                bot.send_photo(uid, elon["rasm"], caption="✅ E'loningiz #" + str(eid) + " tasdiqlandi!\n\n" + text, reply_markup=kb)
            else:
                bot.send_message(uid, "✅ E'loningiz #" + str(eid) + " tasdiqlandi!\n\n" + text, reply_markup=kb)
            try:
                admin_kb2 = types.InlineKeyboardMarkup()
                admin_kb2.add(types.InlineKeyboardButton("🗑 O'chirish", callback_data="del_a_" + str(eid)))
                if uname and uname != "noma'lum":
                    admin_kb2.add(types.InlineKeyboardButton("👤 Muallif", url="https://t.me/" + uname))
                if elon.get("rasm"):
                    bot.send_photo(SOTISH_ADMIN_ID, elon["rasm"], caption="🔔 Yangi SOTISH e'loni\n\n" + text, reply_markup=admin_kb2)
                else:
                    bot.send_message(SOTISH_ADMIN_ID, "🔔 Yangi SOTISH e'loni\n\n" + text, reply_markup=admin_kb2)
            except:
                pass
        else:
            bot.send_message(uid, "✅ E'loningiz #" + str(eid) + " tasdiqlandi!\n\n" + text, reply_markup=kb)
            try:
                kanal_kb = types.InlineKeyboardMarkup()
                if uname and uname != "noma'lum":
                    kanal_kb.add(types.InlineKeyboardButton("💬 Bog'lanish", url="https://t.me/" + uname))
                bot.send_message(KANAL_ID, text, reply_markup=kanal_kb)
            except:
                pass
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("rad_"))
def rad_cb(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    uid = int(call.data.replace("rad_", ""))
    db = load_db()
    if str(uid) in db.get("kutish", {}):
        del db["kutish"][str(uid)]
        save_db(db)
    bot.answer_callback_query(call.id, "Rad etildi.")
    bot.edit_message_caption(
        caption=call.message.caption + "\n\n❌ RAD ETILDI",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    try:
        bot.send_message(
            uid,
            "❌ To'lovingiz rad etildi.\n"
            "Muammo bo'lsa admin bilan bog'laning: @EFUTBAL_STARTUVA10",
            reply_markup=main_kb()
        )
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_a_"))
def admin_del_cb(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    eid = int(call.data.replace("del_a_", ""))
    db = load_db()
    for e in db["elonlar"]:
        if e["id"] == eid:
            e["faol"] = False
            save_db(db)
            bot.answer_callback_query(call.id, "O'chirildi.")
            bot.send_message(call.message.chat.id, "✅ E'lon #" + str(eid) + " o'chirildi.")
            try:
                bot.send_message(e["user_id"], "❌ E'loningiz #" + str(eid) + " admin tomonidan o'chirildi.")
            except:
                pass
            return
    bot.answer_callback_query(call.id, "Topilmadi.")

@bot.message_handler(func=lambda m: m.text in ["❌ Bekor qilish", "🔙 Orqaga"])
def cancel_h(msg):
    uid = msg.from_user.id
    states[uid] = "main"
    udata[uid] = {}
    bot.send_message(msg.chat.id, "❌ Bekor qilindi.", reply_markup=main_kb())

@bot.message_handler(commands=["admin"])
def admin_h(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    db = load_db()
    faol = len([e for e in db.get("elonlar", []) if e["faol"]])
    jami = len(db.get("elonlar", []))
    users = len(db.get("users", {}))
    kutish = len(db.get("kutish", {}))
    text = (
        "👨‍💼 Admin paneli\n\n"
        "👥 Foydalanuvchilar: " + str(users) + "\n"
        "📋 Jami e'lonlar: " + str(jami) + "\n"
        "✅ Faol e'lonlar: " + str(faol) + "\n"
        "⏳ Tasdiq kutayotgan: " + str(kutish)
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 Barcha e'lonlar", callback_data="admin_elonlar"))
    bot.send_message(msg.chat.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "admin_elonlar")
def admin_elonlar_cb(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    db = load_db()
    faol = [e for e in db.get("elonlar", []) if e["faol"]]
    if not faol:
        bot.answer_callback_query(call.id, "E'lon yo'q")
        return
    bot.answer_callback_query(call.id)
    for e in faol[-5:]:
        text = format_elon(e)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑 O'chirish", callback_data="del_a_" + str(e["id"])))
        if e.get("rasm"):
            bot.send_photo(call.message.chat.id, e["rasm"], caption=text, reply_markup=kb)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def unknown_h(msg):
    bot.send_message(msg.chat.id, "👇 Tugmalardan foydalaning.", reply_markup=main_kb())

if __name__ == "__main__":
    print("✅ Bot ishga tushdi!")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print("Xato:", e)
            time.sleep(5)
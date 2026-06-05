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

ADMINS_LIST = {
    "@EFUTBAL_STARTUVA10": "Bosh Admin",
    "@Fuzzsss": "Bot yaratuvchisi",
}

PRICES = (
    "🛍 Akkauntlarga elon berish narxlari:\n\n"
    "💵 0 dan 500 000 gacha — 4 000 som\n"
    "💵 500 000 dan 1 000 000 gacha — 6 000 som\n"
    "💵 1 000 000 dan 5 000 000 gacha — 10 000 som\n"
    "💵 5 000 000 dan 20 000 000 gacha — 15 000 som\n\n"
    "♻ Botda avto tolov qilish imkoniyati mavjud!\n\n"
    "❗ Akkount olaman deb reklama berishingiz ham mumkin!"
)

QOIDALAR = (
    "📚 Qoidalar:\n\n"
    "1️⃣ Har bir foydalanuvchi savdo oldidan akkountni tekshirsin.\n"
    "2️⃣ Spam va soxta elonlar taqiqlanadi.\n"
    "3️⃣ Qoidabuzarlarga cheklov qoyiladi.\n"
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
    return {"elonlar": [], "users": {}}

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
        types.KeyboardButton("➕ Elon berish"),
        types.KeyboardButton("📋 Elonlarim"),
        types.KeyboardButton("👨‍💼 Adminlar"),
        types.KeyboardButton("📚 Qoidalar"),
        types.KeyboardButton("💰 Elon narxlari"),
    )
    return kb

def tur_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("💵 Sotish eloni"),
        types.KeyboardButton("🔎 Olish eloni"),
        types.KeyboardButton("🔙 Orqaga"),
    )
    return kb

def ha_yoq_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton("✅ Ha"), types.KeyboardButton("❌ Yoq"))
    return kb

def obmen_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton("♻ Obmen koraman"), types.KeyboardButton("❌ Obmen yoq"))
    return kb

def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Bekor qilish"))
    return kb

def format_sotish(e):
    google_val = "✅ Ha" if e.get("google") else "❌ Yoq"
    obmen_val = "♻ Koraman" if e.get("obmen") else "❌ Yoq"
    text = (
        "🏪 SOTISH ELONI\n"
        "━━━━━━━━━━━━━━━\n"
        "🆔 Elon: #" + str(e["id"]) + "\n"
        "💰 Narx: " + str(e.get("narx", 0)) + " som\n"
        "🔐 Google: " + google_val + "\n"
        "♻ Obmen: " + obmen_val + "\n"
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
    google_val = "✅ Ha" if e.get("google") else "❌ Yoq"
    text = (
        "🔎 OLISH ELONI\n"
        "━━━━━━━━━━━━━━━\n"
        "🆔 Elon: #" + str(e["id"]) + "\n"
        "💵 Budzhet: " + str(e.get("budzhet", 0)) + " som\n"
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

@bot.message_handler(commands=["start"])
def start_cmd(msg):
    uid = msg.from_user.id
    if not check_sub(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 Kanalga obuna", url="https://t.me/EFOOTBALSTART"))
        kb.add(types.InlineKeyboardButton("✅ Obuna boldim", callback_data="check_sub"))
        bot.send_message(
            msg.chat.id,
            "🚀 Botdan foydalanish uchun kanalga obuna boling:\n\n📢 @EFOOTBALSTART",
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
        "⚽ eFootball akkauntlarini sotish va sotib olish platformasi.",
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
        bot.answer_callback_query(call.id, "Siz hali obuna bolmadingiz!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "📚 Qoidalar")
def qoidalar_h(msg):
    bot.send_message(msg.chat.id, QOIDALAR, reply_markup=main_kb())

@bot.message_handler(func=lambda m: m.text == "💰 Elon narxlari")
def narxlar_h(msg):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✉ Bot egasi", url="https://t.me/EFUTBAL_STARTUVA10"))
    bot.send_message(msg.chat.id, PRICES, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "👨‍💼 Adminlar")
def adminlar_h(msg):
    kb = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for uname in ADMINS_LIST:
        clean = uname.replace("@", "")
        btns.append(types.InlineKeyboardButton("👤 " + uname, url="https://t.me/" + clean))
    kb.add(*btns)
    bot.send_message(msg.chat.id, "👨‍💼 Adminlar royxati:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📋 Elonlarim")
def elonlarim_h(msg):
    uid = msg.from_user.id
    db = load_db()
    my = [e for e in db.get("elonlar", []) if e["user_id"] == uid and e["faol"]]
    if not my:
        bot.send_message(msg.chat.id, "🙅 Sizda aktiv elon topilmadi!", reply_markup=main_kb())
        return
    bot.send_message(msg.chat.id, "📋 Sizning faol elonlaringiz:")
    for e in my:
        text = format_elon(e)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑 Ochirish", callback_data="del_" + str(e["id"])))
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
            bot.answer_callback_query(call.id, "Elon ochirildi.")
            bot.send_message(call.message.chat.id, "✅ Elon #" + str(eid) + " ochirildi.", reply_markup=main_kb())
            return
    bot.answer_callback_query(call.id, "Topilmadi.")

@bot.message_handler(func=lambda m: m.text == "🔍 Akkount qidirish")
def qidiruv_h(msg):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("💵 Sotish elonlari", callback_data="search_sotish"),
        types.InlineKeyboardButton("🔎 Olish elonlari", callback_data="search_olish"),
    )
    bot.send_message(msg.chat.id, "🔍 Qaysi turdagi elonlarni korizmoqchisiz?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["search_sotish", "search_olish"])
def search_cb(call):
    tur = "sotish" if call.data == "search_sotish" else "olish"
    db = load_db()
    elonlar = [e for e in db.get("elonlar", []) if e["tur"] == tur and e["faol"]]
    if not elonlar:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "😔 Hozircha bu turdagi elon yoq.", reply_markup=main_kb())
        return
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📋 " + str(len(elonlar)) + " ta elon topildi:")
    for e in elonlar[-10:]:
        text = format_elon(e)
        kb = types.InlineKeyboardMarkup()
        uname = e.get("username", "")
        if uname and uname != "noma'lum":
            kb.add(types.InlineKeyboardButton("💬 Boglanish", url="https://t.me/" + uname))
        if e.get("rasm"):
            bot.send_photo(call.message.chat.id, e["rasm"], caption=text, reply_markup=kb)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Elon berish")
def elon_berish_h(msg):
    uid = msg.from_user.id
    if not check_sub(uid):
        bot.send_message(msg.chat.id, "❌ Avval kanalga obuna boling!", reply_markup=main_kb())
        return
    states[uid] = "elon_tur"
    udata[uid] = {}
    bot.send_message(msg.chat.id, "📝 Qanday elon berishni xohlaysiz?", reply_markup=tur_kb())

@bot.message_handler(func=lambda m: m.text == "💵 Sotish eloni" and states.get(m.from_user.id) == "elon_tur")
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

@bot.message_handler(func=lambda m: m.text in ["✅ Ha", "❌ Yoq"] and states.get(m.from_user.id) == "sotish_google")
def sotish_google_h(msg):
    uid = msg.from_user.id
    udata[uid]["google"] = msg.text == "✅ Ha"
    states[uid] = "sotish_obmen"
    bot.send_message(msg.chat.id, "♻ Obmen koramisiz?", reply_markup=obmen_kb())

@bot.message_handler(func=lambda m: m.text in ["♻ Obmen koraman", "❌ Obmen yoq"] and states.get(m.from_user.id) == "sotish_obmen")
def sotish_obmen_h(msg):
    uid = msg.from_user.id
    udata[uid]["obmen"] = msg.text == "♻ Obmen koraman"
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
        bot.send_message(msg.chat.id, "📝 Qoshimcha malumot kiriting.\nYoq deb yozsangiz otkazib yuboradi:", reply_markup=cancel_kb())
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Faqat raqam kiriting! Masalan: 500000")

@bot.message_handler(func=lambda m: states.get(m.from_user.id) == "sotish_izoh")
def sotish_izoh_h(msg):
    uid = msg.from_user.id
    if msg.text == "❌ Bekor qilish":
        cancel_h(msg)
        return
    udata[uid]["izoh"] = "" if msg.text.lower() == "yoq" else msg.text
    saqlash(msg, uid)

@bot.message_handler(func=lambda m: m.text == "🔎 Olish eloni" and states.get(m.from_user.id) == "elon_tur")
def olish_start(msg):
    uid = msg.from_user.id
    states[uid] = "olish_budzhet"
    udata[uid]["tur"] = "olish"
    bot.send_message(msg.chat.id, "💵 Budjetingizni kiriting (som):\nMisol: 1000000", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: states.get(m.from_user.id) == "olish_budzhet")
def olish_budzhet_h(msg):
    uid = msg.from_user.id
    if msg.text == "❌ Bekor qilish":
        cancel_h(msg)
        return
    try:
        b = int(msg.text.replace(" ", "").replace(",", ""))
        udata[uid]["budzhet"] = b
        states[uid] = "olish_google"
        bot.send_message(msg.chat.id, "🔐 Google yoki Game Center kerakmi?", reply_markup=ha_yoq_kb())
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Faqat raqam kiriting! Masalan: 1000000")

@bot.message_handler(func=lambda m: m.text in ["✅ Ha", "❌ Yoq"] and states.get(m.from_user.id) == "olish_google")
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
    saqlash(msg, uid)

def saqlash(msg, uid):
    db = load_db()
    eid = next_id()
    elon = {
        "id": eid,
        "user_id": uid,
        "username": msg.from_user.username if msg.from_user.username else "noma'lum",
        "ism": msg.from_user.first_name,
        "tur": udata[uid].get("tur"),
        "faol": True,
        "sana": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    if elon["tur"] == "sotish":
        elon["rasm"] = udata[uid].get("rasm")
        elon["google"] = udata[uid].get("google", False)
        elon["obmen"] = udata[uid].get("obmen", False)
        elon["narx"] = udata[uid].get("narx", 0)
        elon["izoh"] = udata[uid].get("izoh", "")
    else:
        elon["budzhet"] = udata[uid].get("budzhet", 0)
        elon["google"] = udata[uid].get("google", False)
        elon["tavsif"] = udata[uid].get("tavsif", "")

    if "elonlar" not in db:
        db["elonlar"] = []
    db["elonlar"].append(elon)
    save_db(db)

    states[uid] = "main"
    udata[uid] = {}

    text = "✅ Eloningiz #" + str(eid) + " saqlandi!\n\n" + format_elon(elon)
    uname = elon.get("username", "")

    if elon["tur"] == "sotish":
        kb = types.InlineKeyboardMarkup()
        if uname and uname != "noma'lum":
            kb.add(types.InlineKeyboardButton("💬 Boglanish", url="https://t.me/" + uname))
        if elon.get("rasm"):
            bot.send_photo(msg.chat.id, elon["rasm"], caption=text, reply_markup=kb)
        else:
            bot.send_message(msg.chat.id, text, reply_markup=kb)
        bot.send_message(msg.chat.id, "🏠 Bosh menyu:", reply_markup=main_kb())
        admin_text = "🔔 Yangi SOTISH eloni #" + str(eid) + "\n\n" + format_elon(elon)
        admin_kb = types.InlineKeyboardMarkup()
        if uname and uname != "noma'lum":
            admin_kb.add(types.InlineKeyboardButton("👤 Muallif", url="https://t.me/" + uname))
        admin_kb.add(types.InlineKeyboardButton("🗑 Ochirish", callback_data="del_a_" + str(eid)))
        try:
            if elon.get("rasm"):
                bot.send_photo(SOTISH_ADMIN_ID, elon["rasm"], caption=admin_text, reply_markup=admin_kb)
            else:
                bot.send_message(SOTISH_ADMIN_ID, admin_text, reply_markup=admin_kb)
        except:
            pass
    else:
        kb = types.InlineKeyboardMarkup()
        if uname and uname != "noma'lum":
            kb.add(types.InlineKeyboardButton("💬 Boglanish", url="https://t.me/" + uname))
        bot.send_message(msg.chat.id, text, reply_markup=kb)
        bot.send_message(msg.chat.id, "🏠 Bosh menyu:", reply_markup=main_kb())
        kanal_text = format_elon(elon)
        kanal_kb = types.InlineKeyboardMarkup()
        if uname and uname != "noma'lum":
            kanal_kb.add(types.InlineKeyboardButton("💬 Boglanish", url="https://t.me/" + uname))
        try:
            bot.send_message(KANAL_ID, kanal_text, reply_markup=kanal_kb)
        except:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_a_"))
def admin_del_cb(call):
    eid = int(call.data.replace("del_a_", ""))
    db = load_db()
    for e in db["elonlar"]:
        if e["id"] == eid:
            e["faol"] = False
            save_db(db)
            bot.answer_callback_query(call.id, "Elon ochirildi.")
            bot.send_message(call.message.chat.id, "✅ Elon #" + str(eid) + " ochirildi.")
            try:
                bot.send_message(e["user_id"], "❌ Eloningiz #" + str(eid) + " admin tomonidan ochirildi.")
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
    text = (
        "👨‍💼 Admin paneli\n\n"
        "👥 Foydalanuvchilar: " + str(users) + "\n"
        "📋 Jami elonlar: " + str(jami) + "\n"
        "✅ Faol elonlar: " + str(faol)
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 Barcha elonlar", callback_data="admin_elonlar"))
    bot.send_message(msg.chat.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "admin_elonlar")
def admin_elonlar_cb(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    db = load_db()
    faol = [e for e in db.get("elonlar", []) if e["faol"]]
    if not faol:
        bot.answer_callback_query(call.id, "Elon yoq")
        return
    bot.answer_callback_query(call.id)
    for e in faol[-5:]:
        text = format_elon(e)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🗑 Ochirish", callback_data="del_a_" + str(e["id"])))
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
"""
Steganografiya Telegram Bot — To'liq versiya (v5) — Railway uchun
===================================================================
Imkoniyatlar:
  - Rasm ichiga matn yashirish/chiqarish (LSB, NumPy bilan tez)
  - Parol bilan shifrlash (ixtiyoriy, Fernet/PBKDF2)
  - Ko'p tillilik: O'zbek / Русский / English
  - /cancel — jarayonni istalgan vaqtda bekor qilish
  - Flood (haddan tashqari tez-tez yozish) himoyasi
  - O'z-o'zini tekshirish: yashirilgan matn saqlangach avtomatik tekshiriladi
  - /feedback — foydalanuvchi fikr-mulohazasini administratorga yuborish
  - /stats — faqat administrator uchun statistika
  - "🔁 Yana yashirish" tugmasi
  - Kunlik limit (standart: 3 marta/kun, admin uchun cheksiz)
  - 5 daqiqa javobsiz qolgan sessiyalarni avtomatik tozalash
  - Telegram flood-limit (429) xatosida avtomatik qayta urinish
  - Og'ir hisoblashlar alohida threadlarda (bot bloklanmaydi, ko'p
    foydalanuvchi bir vaqtda ishlatganda barqaror ishlaydi)

Railway'ga deploy: DEPLOY.md faylidagi ko'rsatmalarga qarang.
Muhim: TELEGRAM_BOT_TOKEN va ADMIN_ID muhit o'zgaruvchilarini albatta o'rnating.
"""

import io
import os
import time
import json
import base64
import asyncio
import logging
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

import numpy as np
from PIL import Image
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from telegram import (
    Update,
    InputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ChatAction
from telegram.error import BadRequest, RetryAfter, TimedOut
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============ SOZLAMALAR ============
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8355611778"))
END_MARKER = "#####END#####"
PROGRESS_STEPS = 5
FLOOD_WAIT_SECONDS = 1.5
STATS_FILE = "stats.json"
USAGE_FILE = "usage.json"
PLAIN_PREFIX = "P0:"
ENC_PREFIX = "P1:"

DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", "3"))          # bir kunda nechta amal (yashirish+chiqarish)
STALE_TIMEOUT_SECONDS = 5 * 60                                  # 5 daqiqa javobsiz qolsa, holat tozalanadi
CLEANUP_CHECK_INTERVAL = 60                                      # tozalash tekshiruvi har necha soniyada

# Og'ir NumPy hisoblashlarini asosiy oqimdan (event loop) ajratib, alohida
# threadlarda bajarish uchun havza. Bu bot bir nechta foydalanuvchini bir
# vaqtda (100-200 kishi) xizmat qilganda "qotib qolmasligi"ni ta'minlaydi.
MAX_WORKERS = int(os.environ.get("STEGO_MAX_WORKERS", "4"))
EXECUTOR = ThreadPoolExecutor(max_workers=MAX_WORKERS)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

user_states: Dict[int, str] = {}
user_images: Dict[int, Image.Image] = {}
user_secret_text: Dict[int, str] = {}          # parol so'ralganda matnni vaqtincha saqlash
user_pending_payload: Dict[int, str] = {}      # chiqarishda parol talab qilinsa, payloadni saqlash
user_lang: Dict[str, str] = {}                 # user_id(str) -> "uz"/"ru"/"en"
last_action_time: Dict[int, float] = {}        # flood himoyasi uchun

CB_HIDE = "menu_hide"
CB_EXTRACT = "menu_extract"
CB_HELP = "menu_help"
CB_ABOUT = "menu_about"
CB_CANCEL = "menu_cancel"
CB_BACK = "menu_back"
CB_LANG = "menu_lang"
CB_LANG_UZ = "lang_uz"
CB_LANG_RU = "lang_ru"
CB_LANG_EN = "lang_en"
CB_PWD_YES = "pwd_yes"
CB_PWD_NO = "pwd_no"
CB_HIDE_AGAIN = "hide_again"


# ============ KO'P TILLILIK ============

TEXTS = {
    "uz": {
        "welcome": "👋 <b>Steganografiya Botiga xush kelibsiz!</b>\n\nRasm ichiga maxfiy matn yashiring va uni qayta chiqarib oling.\n\nTanlang:",
        "btn_hide": "🔒 Matn yashirish",
        "btn_extract": "🔓 Matnni chiqarish",
        "btn_help": "ℹ️ Yordam",
        "btn_about": "🤖 Bot haqida",
        "btn_lang": "🌐 Til",
        "btn_cancel": "❌ Bekor qilish",
        "btn_back": "⬅️ Orqaga",
        "btn_yes": "✅ Ha",
        "btn_no": "🚫 Yo'q",
        "btn_hide_again": "🔁 Yana yashirish",
        "choose_lang": "🌐 Tilni tanlang:",
        "lang_set": "✅ Til o'zbekchaga o'rnatildi.",
        "prompt_send_image_hide": "📷 Menga rasmni <b>fayl</b> sifatida yuboring (📎 → File/Document, PNG tavsiya etiladi).",
        "prompt_send_image_extract": "📷 Ichida yashirin matn bo'lgan rasmni yuboring.",
        "compressed_warning": "\n\n⚠️ Bu rasm Telegram tomonidan siqilgan bo'lishi mumkin — keyingi safar fayl (📎 → File) sifatida yuboring.",
        "open_image_error": "❌ Rasmni ochib bo'lmadi. Boshqa fayl sinab ko'ring.",
        "capacity_info": "📐 Rasm: {w}x{h}, taxminan {cap} belgigacha sig'adi.",
        "ask_password": "🔑 Matnni parol bilan himoyalashni xohlaysizmi?",
        "ask_password_set": "🔑 Parolni kiriting (buni eslab qoling — parolsiz matnni chiqarib bo'lmaydi!):",
        "prompt_enter_text": "✍️ Endi yashirmoqchi bo'lgan matnni yozib yuboring.",
        "hiding_status": "🔒 Matn rasmga yashirilmoqda...",
        "extracting_status": "🔍 Yashirin matn qidirilmoqda...",
        "verifying_status": "🔎 Natija tekshirilmoqda...",
        "done": "✅ Tayyor!",
        "capacity_exceeded": "❌ Matn juda uzun! Bu rasm maksimal {cap} belgi sig'diradi, sizning matningiz {n} belgi.",
        "no_hidden_text": "❌ Bu rasmda yashirin matn topilmadi.",
        "extracted_prefix": "🔓 <b>Yashirilgan matn:</b>\n\n{text}",
        "ask_password_check": "🔑 Bu matn parol bilan himoyalangan. Parolni kiriting:",
        "wrong_password": "❌ Parol noto'g'ri. Qaytadan urinib ko'ring yoki /cancel bilan bekor qiling.",
        "cancelled": "🚫 Jarayon bekor qilindi.",
        "nothing_to_cancel": "Bekor qilinadigan jarayon yo'q.",
        "flood_wait": "⏳ Juda tez yozyapsiz, biroz kuting...",
        "result_caption": "✅ Matn rasmga muvaffaqiyatli yashirildi!\nDiqqat: faylni PNG holida saqlang, JPEG'ga aylantirmang — aks holda matn yo'qoladi.",
        "verify_failed": "❌ Ichki tekshiruvda xatolik: natija rasmda matn to'g'ri saqlanmadi. Qaytadan urinib ko'ring.",
        "unexpected_error": "❌ Kutilmagan xatolik yuz berdi. Qaytadan urinib ko'ring.",
        "no_image_found": "Xatolik: rasm topilmadi. Qaytadan boshlang.",
        "choose_from_menu": "Boshlash uchun menyudan tanlang:",
        "select_from_menu_first": "Iltimos, avval menyudan tanlang:",
        "feedback_prompt": "💬 Fikr-mulohazangizni yozing, men uni administratorga yuboraman:",
        "feedback_thanks": "🙏 Rahmat! Fikringiz administratorga yuborildi.",
        "help_text": (
            "ℹ️ <b>Yordam</b>\n\n"
            "🔒 <b>Matn yashirish</b> — rasm yuborasiz, ixtiyoriy parol qo'yasiz, so'ng matningizni kiritasiz.\n\n"
            "🔓 <b>Matnni chiqarish</b> — yashirin matni bor rasmni yuborasiz (parol qo'yilgan bo'lsa, so'raladi).\n\n"
            "/cancel — joriy jarayonni bekor qilish\n"
            "/feedback — fikr-mulohaza yuborish\n\n"
            "⚠️ Rasmni <u>fayl</u> sifatida (📎 → File) yuboring, oddiy rasm sifatida emas."
        ),
        "about_text": (
            "🤖 <b>Steganografiya Bot haqida</b>\n\n"
            "Bu bot — istalgan rasm ichiga maxfiy matn yashirish va uni qayta chiqarib olish uchun yaratilgan zamonaviy vosita.\n\n"
            "<b>🔧 Ishlash tamoyili:</b>\n"
            "LSB (Least Significant Bit) algoritmi orqali matningiz rasm piksellarining eng kichik bitlariga joylashtiriladi — natijada rasm ko'rinishi umuman o'zgarmaydi, lekin ichida maxfiy ma'lumot saqlanadi.\n\n"
            "<b>✨ Asosiy imkoniyatlar:</b>\n"
            "• 🔒 Parol bilan qo'shimcha shifrlash (PBKDF2 + Fernet)\n"
            "• 🌐 3 tilda ishlash: O'zbek, Rus, Ingliz\n"
            "• ⚡ NumPy asosida yuqori tezlik\n"
            "• 🔎 O'z-o'zini tekshirish — xato ehtimoli nolga yaqin\n"
            "• 📊 Real vaqtda jarayon foizi\n\n"
            "<b>👨‍💻 Dasturchi:</b> @Fuzzsss"
        ),
        "stats_admin_only": "⛔ Bu buyruq faqat administrator uchun.",
        "stats_report": "📊 <b>Statistika</b>\n\n👥 Foydalanuvchilar: {users}\n🔒 Yashirilgan: {hidden}\n🔓 Chiqarilgan: {extracted}",
        "limit_reached": "⛔ Kunlik limitga yetdingiz (kuniga {limit} marta). Ertaga qayta urinib ko'ring.",
        "session_expired": "⏳ 5 daqiqa javob bo'lmagani uchun jarayon avtomatik bekor qilindi. Qaytadan boshlash uchun /start bosing.",
    },
    "ru": {
        "welcome": "👋 <b>Добро пожаловать в Стегано-бот!</b>\n\nСкройте секретный текст в изображении и извлеките его обратно.\n\nВыберите действие:",
        "btn_hide": "🔒 Скрыть текст",
        "btn_extract": "🔓 Извлечь текст",
        "btn_help": "ℹ️ Помощь",
        "btn_about": "🤖 О боте",
        "btn_lang": "🌐 Язык",
        "btn_cancel": "❌ Отмена",
        "btn_back": "⬅️ Назад",
        "btn_yes": "✅ Да",
        "btn_no": "🚫 Нет",
        "btn_hide_again": "🔁 Скрыть ещё раз",
        "choose_lang": "🌐 Выберите язык:",
        "lang_set": "✅ Язык изменён на русский.",
        "prompt_send_image_hide": "📷 Отправьте изображение <b>файлом</b> (📎 → File/Document, рекомендуется PNG).",
        "prompt_send_image_extract": "📷 Отправьте изображение со скрытым текстом.",
        "compressed_warning": "\n\n⚠️ Это изображение могло быть сжато Telegram — в следующий раз отправляйте файлом (📎 → File).",
        "open_image_error": "❌ Не удалось открыть изображение. Попробуйте другой файл.",
        "capacity_info": "📐 Изображение: {w}x{h}, вмещает примерно {cap} символов.",
        "ask_password": "🔑 Хотите защитить текст паролем?",
        "ask_password_set": "🔑 Введите пароль (запомните его — без пароля текст не извлечь!):",
        "prompt_enter_text": "✍️ Теперь отправьте текст, который нужно скрыть.",
        "hiding_status": "🔒 Скрываем текст в изображении...",
        "extracting_status": "🔍 Ищем скрытый текст...",
        "verifying_status": "🔎 Проверяем результат...",
        "done": "✅ Готово!",
        "capacity_exceeded": "❌ Текст слишком длинный! Максимум для этого изображения: {cap} символов, у вас {n}.",
        "no_hidden_text": "❌ В этом изображении скрытый текст не найден.",
        "extracted_prefix": "🔓 <b>Скрытый текст:</b>\n\n{text}",
        "ask_password_check": "🔑 Этот текст защищён паролем. Введите пароль:",
        "wrong_password": "❌ Неверный пароль. Попробуйте снова или отмените командой /cancel.",
        "cancelled": "🚫 Процесс отменён.",
        "nothing_to_cancel": "Нечего отменять.",
        "flood_wait": "⏳ Слишком быстро, подождите немного...",
        "result_caption": "✅ Текст успешно скрыт в изображении!\nВажно: сохраните файл в формате PNG, не конвертируйте в JPEG — иначе текст будет утерян.",
        "verify_failed": "❌ Ошибка проверки: текст не сохранился корректно. Попробуйте снова.",
        "unexpected_error": "❌ Произошла непредвиденная ошибка. Попробуйте снова.",
        "no_image_found": "Ошибка: изображение не найдено. Начните заново.",
        "choose_from_menu": "Выберите действие в меню:",
        "select_from_menu_first": "Пожалуйста, сначала выберите действие в меню:",
        "feedback_prompt": "💬 Напишите ваш отзыв, я передам его администратору:",
        "feedback_thanks": "🙏 Спасибо! Ваш отзыв отправлен администратору.",
        "help_text": (
            "ℹ️ <b>Помощь</b>\n\n"
            "🔒 <b>Скрыть текст</b> — отправьте изображение, при желании задайте пароль, затем введите текст.\n\n"
            "🔓 <b>Извлечь текст</b> — отправьте изображение со скрытым текстом (если задан пароль, он будет запрошен).\n\n"
            "/cancel — отменить текущий процесс\n"
            "/feedback — отправить отзыв\n\n"
            "⚠️ Отправляйте изображение <u>файлом</u> (📎 → File), а не как обычное фото."
        ),
        "about_text": (
            "🤖 <b>О боте стеганографии</b>\n\n"
            "Этот бот — современный инструмент для скрытия секретного текста внутри изображения и его последующего извлечения.\n\n"
            "<b>🔧 Принцип работы:</b>\n"
            "С помощью алгоритма LSB (Least Significant Bit) ваш текст записывается в младшие биты пикселей изображения — внешний вид картинки не меняется, но внутри неё хранится скрытая информация.\n\n"
            "<b>✨ Основные возможности:</b>\n"
            "• 🔒 Дополнительное шифрование паролем (PBKDF2 + Fernet)\n"
            "• 🌐 Поддержка 3 языков: узбекский, русский, английский\n"
            "• ⚡ Высокая скорость благодаря NumPy\n"
            "• 🔎 Автоматическая проверка результата — вероятность ошибки минимальна\n"
            "• 📊 Прогресс в реальном времени\n\n"
            "<b>👨‍💻 Разработчик:</b> @Fuzzsss"
        ),
        "stats_admin_only": "⛔ Эта команда только для администратора.",
        "stats_report": "📊 <b>Статистика</b>\n\n👥 Пользователи: {users}\n🔒 Скрыто: {hidden}\n🔓 Извлечено: {extracted}",
        "limit_reached": "⛔ Вы достигли дневного лимита ({limit} раз(а) в день). Попробуйте завтра.",
        "session_expired": "⏳ Процесс отменён автоматически из-за 5 минут бездействия. Нажмите /start, чтобы начать заново.",
    },
    "en": {
        "welcome": "👋 <b>Welcome to the Steganography Bot!</b>\n\nHide a secret message inside an image and extract it back.\n\nChoose an option:",
        "btn_hide": "🔒 Hide text",
        "btn_extract": "🔓 Extract text",
        "btn_help": "ℹ️ Help",
        "btn_about": "🤖 About",
        "btn_lang": "🌐 Language",
        "btn_cancel": "❌ Cancel",
        "btn_back": "⬅️ Back",
        "btn_yes": "✅ Yes",
        "btn_no": "🚫 No",
        "btn_hide_again": "🔁 Hide again",
        "choose_lang": "🌐 Choose a language:",
        "lang_set": "✅ Language set to English.",
        "prompt_send_image_hide": "📷 Send me the image as a <b>file</b> (📎 → File/Document, PNG recommended).",
        "prompt_send_image_extract": "📷 Send the image that contains a hidden message.",
        "compressed_warning": "\n\n⚠️ This image may have been compressed by Telegram — next time send it as a file (📎 → File).",
        "open_image_error": "❌ Couldn't open the image. Try another file.",
        "capacity_info": "📐 Image: {w}x{h}, holds up to about {cap} characters.",
        "ask_password": "🔑 Do you want to protect the text with a password?",
        "ask_password_set": "🔑 Enter a password (remember it — without it the text can't be recovered!):",
        "prompt_enter_text": "✍️ Now send the text you want to hide.",
        "hiding_status": "🔒 Hiding text in the image...",
        "extracting_status": "🔍 Searching for hidden text...",
        "verifying_status": "🔎 Verifying the result...",
        "done": "✅ Done!",
        "capacity_exceeded": "❌ Text is too long! This image holds at most {cap} characters, yours has {n}.",
        "no_hidden_text": "❌ No hidden text found in this image.",
        "extracted_prefix": "🔓 <b>Hidden text:</b>\n\n{text}",
        "ask_password_check": "🔑 This text is password-protected. Enter the password:",
        "wrong_password": "❌ Wrong password. Try again or cancel with /cancel.",
        "cancelled": "🚫 Process cancelled.",
        "nothing_to_cancel": "Nothing to cancel.",
        "flood_wait": "⏳ You're sending messages too fast, please wait...",
        "result_caption": "✅ Text successfully hidden in the image!\nNote: keep the file as PNG, don't convert to JPEG — otherwise the text will be lost.",
        "verify_failed": "❌ Verification failed: the text wasn't stored correctly. Please try again.",
        "unexpected_error": "❌ An unexpected error occurred. Please try again.",
        "no_image_found": "Error: image not found. Please start over.",
        "choose_from_menu": "Choose an option from the menu:",
        "select_from_menu_first": "Please choose an option from the menu first:",
        "feedback_prompt": "💬 Write your feedback, I'll forward it to the administrator:",
        "feedback_thanks": "🙏 Thanks! Your feedback has been sent to the administrator.",
        "help_text": (
            "ℹ️ <b>Help</b>\n\n"
            "🔒 <b>Hide text</b> — send an image, optionally set a password, then enter your text.\n\n"
            "🔓 <b>Extract text</b> — send an image with hidden text (a password will be requested if set).\n\n"
            "/cancel — cancel the current process\n"
            "/feedback — send feedback\n\n"
            "⚠️ Send the image as a <u>file</u> (📎 → File), not as a regular photo."
        ),
        "about_text": (
            "🤖 <b>About the Steganography Bot</b>\n\n"
            "This bot is a modern tool for hiding secret text inside an image and extracting it back whenever needed.\n\n"
            "<b>🔧 How it works:</b>\n"
            "Using the LSB (Least Significant Bit) algorithm, your text is written into the least significant bits of the image's pixels — the image looks completely unchanged, but it secretly holds your data.\n\n"
            "<b>✨ Key features:</b>\n"
            "• 🔒 Optional password encryption (PBKDF2 + Fernet)\n"
            "• 🌐 Available in 3 languages: Uzbek, Russian, English\n"
            "• ⚡ High speed powered by NumPy\n"
            "• 🔎 Built-in self-verification — near-zero error rate\n"
            "• 📊 Real-time progress display\n\n"
            "<b>👨‍💻 Developer:</b> @Fuzzsss"
        ),
        "stats_admin_only": "⛔ This command is for the administrator only.",
        "stats_report": "📊 <b>Statistics</b>\n\n👥 Users: {users}\n🔒 Hidden: {hidden}\n🔓 Extracted: {extracted}",
        "limit_reached": "⛔ You've reached the daily limit ({limit} times per day). Try again tomorrow.",
        "session_expired": "⏳ The process was cancelled automatically after 5 minutes of inactivity. Press /start to begin again.",
    },
}


def get_lang(user_id: int) -> str:
    return user_lang.get(str(user_id), "uz")


def t(user_id: int, key: str, **kwargs) -> str:
    lang = get_lang(user_id)
    text = TEXTS.get(lang, TEXTS["uz"]).get(key, TEXTS["uz"].get(key, key))
    return text.format(**kwargs) if kwargs else text


# ============ STATISTIKA (oddiy JSON fayl) ============
# Eslatma: Railway'da disk vaqtinchalik — qayta deploy qilinganda tozalanishi
# mumkin. Doimiy statistika kerak bo'lsa, Railway'ning PostgreSQL qo'shimchasi
# tavsiya etiladi.

def load_stats() -> dict:
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            data["users"] = set(data.get("users", []))
            return data
    except Exception:
        return {"users": set(), "hidden_count": 0, "extracted_count": 0}


def save_stats():
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "users": list(stats["users"]),
                    "hidden_count": stats["hidden_count"],
                    "extracted_count": stats["extracted_count"],
                },
                f,
            )
    except Exception as e:
        logger.warning("Statistikani saqlab bo'lmadi: %s", e)


stats = load_stats()


def track_user(user_id: int):
    stats["users"].add(user_id)
    save_stats()


def track_hidden():
    stats["hidden_count"] += 1
    save_stats()


def track_extracted():
    stats["extracted_count"] += 1
    save_stats()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ============ KUNLIK LIMIT ============
# Eslatma: Railway diskida vaqtinchalik saqlanadi (stats.json bilan bir xil holat).

def load_usage() -> dict:
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_usage():
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(usage_data, f)
    except Exception as e:
        logger.warning("Foydalanish statistikasini saqlab bo'lmadi: %s", e)


usage_data: dict = load_usage()


def get_remaining_quota(user_id: int) -> int:
    """Admin uchun cheksiz; boshqalar uchun bugungi qolgan urinishlar sonini qaytaradi."""
    if is_admin(user_id):
        return 999
    today = date.today().isoformat()
    record = usage_data.get(str(user_id))
    if not record or record.get("date") != today:
        return DAILY_LIMIT
    return max(0, DAILY_LIMIT - record.get("count", 0))


def register_usage(user_id: int):
    """Amal (yashirish/chiqarish) muvaffaqiyatli bajarilganda chaqiriladi."""
    if is_admin(user_id):
        return
    today = date.today().isoformat()
    record = usage_data.get(str(user_id))
    if not record or record.get("date") != today:
        record = {"date": today, "count": 0}
    record["count"] += 1
    usage_data[str(user_id)] = record
    save_usage()


# ============ FLOOD HIMOYASI ============

def is_flooding(user_id: int) -> bool:
    now = time.monotonic()
    last = last_action_time.get(user_id, 0)
    last_action_time[user_id] = now
    return (now - last) < FLOOD_WAIT_SECONDS


# ============ TELEGRAM API: FLOOD-LIMIT XATOSIDA QAYTA URINISH ============

async def api_call(coro_factory, retries: int = 2):
    """
    Telegram'ning 429 (RetryAfter) yoki vaqtinchalik tarmoq xatolarida
    avtomatik qayta urinadi. Bu 100-200 kishi bir vaqtda ishlatganda
    xabarlar tushib qolmasligini ta'minlaydi.
    """
    for attempt in range(retries + 1):
        try:
            return await coro_factory()
        except RetryAfter as e:
            wait = getattr(e, "retry_after", 3) + 0.5
            logger.warning("Telegram flood-limit: %s soniya kutilmoqda (urinish %s)", wait, attempt + 1)
            await asyncio.sleep(wait)
        except TimedOut:
            await asyncio.sleep(1.5)
    # Oxirgi urinish — xato bo'lsa, chaqiruvchiga otiladi
    return await coro_factory()


# ============ SHIFRLASH (parol bilan himoyalash) ============

def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_payload(secret_text: str, password: str) -> str:
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    token = Fernet(key).encrypt(secret_text.encode("utf-8"))
    return ENC_PREFIX + base64.urlsafe_b64encode(salt).decode() + "::" + token.decode()


def decrypt_payload(payload: str, password: str) -> Optional[str]:
    try:
        body = payload[len(ENC_PREFIX):]
        salt_b64, token = body.split("::", 1)
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        key = _derive_key(password, salt)
        return Fernet(key).decrypt(token.encode()).decode("utf-8")
    except (InvalidToken, ValueError, Exception):
        return None


# ============ STEGANOGRAFIYA FUNKSIYALARI (NumPy — tez) ============

def _text_to_bits(text: str) -> np.ndarray:
    byte_arr = np.frombuffer(text.encode("utf-8", errors="ignore"), dtype=np.uint8)
    return np.unpackbits(byte_arr)


def _bits_to_text(bits: np.ndarray) -> str:
    n = (len(bits) // 8) * 8
    byte_arr = np.packbits(bits[:n])
    return byte_arr.tobytes().decode("utf-8", errors="ignore")


def image_capacity_chars(image: Image.Image) -> int:
    width, height = image.size
    return (width * height * 3) // 8


def _hide_chunk_sync(flat: np.ndarray, bits: np.ndarray, start: int, end: int):
    """Bitta bo'lakni piksellarga yozadi (bloklovchi, executor'da bajariladi)."""
    segment = flat[start:end]
    flat[start:end] = (segment & 0xFE) | bits[start:end]


def _extract_chunk_sync(flat: np.ndarray, end: int) -> str:
    """Boshidan `end`gacha bo'lgan bitlarni matnga aylantiradi (bloklovchi)."""
    bits_chunk = flat[:end] & 1
    return _bits_to_text(bits_chunk)


async def hide_payload_in_image_progress(image: Image.Image, payload: str, on_progress=None) -> Image.Image:
    image = image.convert("RGB")
    max_capacity = image_capacity_chars(image)
    if len(payload) > max_capacity:
        raise ValueError("capacity_exceeded")

    if on_progress:
        await on_progress(10)

    loop = asyncio.get_event_loop()
    # Og'ir amallarni (massiv yaratish, bit yozish) alohida threadga chiqaramiz —
    # shu payt bot boshqa foydalanuvchilarga ham javob berishda davom etadi.
    arr = await loop.run_in_executor(EXECUTOR, lambda: np.array(image, dtype=np.uint8))
    flat = arr.reshape(-1)
    bits = _text_to_bits(payload + END_MARKER)
    total_bits = len(bits)

    if on_progress:
        await on_progress(25)

    chunk_size = max(1, -(-total_bits // PROGRESS_STEPS))
    for step in range(PROGRESS_STEPS):
        start = step * chunk_size
        end = min(start + chunk_size, total_bits)
        if start >= end:
            break
        await loop.run_in_executor(EXECUTOR, _hide_chunk_sync, flat, bits, start, end)
        if on_progress:
            percent = 25 + int(60 * (end / total_bits))
            await on_progress(min(percent, 85))

    result_image = await loop.run_in_executor(EXECUTOR, lambda: Image.fromarray(arr, mode="RGB"))
    if on_progress:
        await on_progress(95)
    return result_image


async def extract_payload_from_image_progress(image: Image.Image, on_progress=None) -> Optional[str]:
    image = image.convert("RGB")
    loop = asyncio.get_event_loop()
    arr = await loop.run_in_executor(EXECUTOR, lambda: np.array(image, dtype=np.uint8))
    flat = arr.reshape(-1)

    if on_progress:
        await on_progress(15)

    total_len = len(flat)

    for step in range(PROGRESS_STEPS):
        start = step * (total_len // PROGRESS_STEPS)
        end = total_len if step == PROGRESS_STEPS - 1 else (step + 1) * (total_len // PROGRESS_STEPS)
        if start >= end:
            continue

        text_so_far = await loop.run_in_executor(EXECUTOR, _extract_chunk_sync, flat, end)
        if END_MARKER in text_so_far:
            found = text_so_far.split(END_MARKER)[0]
            if on_progress:
                await on_progress(100)
            return found

        if on_progress:
            percent = 15 + int(80 * (end / total_len))
            await on_progress(min(percent, 95))

    return None


# ============ TUGMALI MENYULAR ============

def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(t(user_id, "btn_hide"), callback_data=CB_HIDE)],
        [InlineKeyboardButton(t(user_id, "btn_extract"), callback_data=CB_EXTRACT)],
        [
            InlineKeyboardButton(t(user_id, "btn_help"), callback_data=CB_HELP),
            InlineKeyboardButton(t(user_id, "btn_about"), callback_data=CB_ABOUT),
        ],
        [InlineKeyboardButton(t(user_id, "btn_lang"), callback_data=CB_LANG)],
    ]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(user_id, "btn_cancel"), callback_data=CB_CANCEL)]])


def back_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t(user_id, "btn_back"), callback_data=CB_BACK)]])


def password_choice_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(t(user_id, "btn_yes"), callback_data=CB_PWD_YES),
            InlineKeyboardButton(t(user_id, "btn_no"), callback_data=CB_PWD_NO),
        ]]
    )


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data=CB_LANG_UZ)],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data=CB_LANG_RU)],
            [InlineKeyboardButton("🇬🇧 English", callback_data=CB_LANG_EN)],
        ]
    )


def result_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(user_id, "btn_hide_again"), callback_data=CB_HIDE_AGAIN)]]
    )


# ============ YORDAMCHI: XAVFSIZ TAHRIRLASH ============

async def safe_edit(query, text: str, reply_markup=None, parse_mode=None):
    try:
        await api_call(lambda: query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode))
    except BadRequest as e:
        logger.info("edit_message_text ishlamadi (%s), yangi xabar yuborilmoqda.", e)
        try:
            await api_call(lambda: query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode))
        except Exception:
            await api_call(
                lambda: query.get_bot().send_message(
                    chat_id=query.from_user.id, text=text, reply_markup=reply_markup, parse_mode=parse_mode
                )
            )


SPINNER_FRAMES = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]


def progress_bar(percent: int) -> str:
    filled = percent // 10
    bar = f"[{'█' * filled}{'░' * (10 - filled)}] {percent}%"
    if percent >= 100:
        return f"✅ {bar}"
    icon = SPINNER_FRAMES[filled % len(SPINNER_FRAMES)]
    return f"{icon} {bar}"


async def make_progress_updater(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, label: str):
    last_percent = {"value": -1}

    async def update(percent: int):
        percent = max(0, min(100, percent))
        if percent == last_percent["value"]:
            return
        last_percent["value"] = percent
        try:
            await api_call(
                lambda: context.bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=f"{label}\n\n{progress_bar(percent)}"
                )
            )
        except BadRequest:
            pass

    return update


def reset_user_state(user_id: int):
    user_states.pop(user_id, None)
    user_images.pop(user_id, None)
    user_secret_text.pop(user_id, None)
    user_pending_payload.pop(user_id, None)


async def cleanup_stale_sessions(context: ContextTypes.DEFAULT_TYPE):
    """
    Har CLEANUP_CHECK_INTERVAL soniyada ishga tushadi: 5 daqiqadan ortiq
    javob bermagan (rasm yuklab qo'yib ketib qolgan) foydalanuvchilarning
    vaqtinchalik holatini (rasm, parol va h.k.) xotiradan tozalaydi.

    MUHIM: bu faqat "jarayon holati"ni tozalaydi. Foydalanuvchiga allaqachon
    yuborilgan natija-rasm ichidagi matn bunga bog'liq emas — chunki matn
    rasmning piksellarida saqlanadi, bot xotirasida emas. Shuning uchun
    tozalashdan keyin ham o'sha rasmni /extract orqali istalgan vaqtda
    ochish mumkin bo'lib qoladi.
    """
    now = time.monotonic()
    stale_users = [
        uid for uid in list(user_states.keys())
        if now - last_action_time.get(uid, 0) > STALE_TIMEOUT_SECONDS
    ]
    for uid in stale_users:
        reset_user_state(uid)
        try:
            await context.bot.send_message(chat_id=uid, text=t(uid, "session_expired"))
        except Exception:
            pass  # foydalanuvchi botni bloklagan bo'lishi mumkin — e'tiborsiz qoldiramiz
    if stale_users:
        logger.info("Tozalandi: %s ta eskirgan sessiya", len(stale_users))


# ============ FLOOD DEKORATORI ============

def flood_guard(handler):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user and is_flooding(user.id):
            msg = t(user.id, "flood_wait")
            if update.callback_query:
                await update.callback_query.answer(msg, show_alert=False)
            elif update.message:
                await update.message.reply_text(msg)
            return
        return await handler(update, context)

    return wrapped


# ============ ASOSIY HANDLERLAR ============

@flood_guard
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reset_user_state(user_id)
    track_user(user_id)
    await update.message.reply_text(
        t(user_id, "welcome"), reply_markup=main_menu_keyboard(user_id), parse_mode="HTML"
    )


@flood_guard
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    had_state = user_id in user_states
    reset_user_state(user_id)
    key = "cancelled" if had_state else "nothing_to_cancel"
    await update.message.reply_text(t(user_id, key), reply_markup=main_menu_keyboard(user_id))


@flood_guard
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(t(user_id, "help_text"), reply_markup=back_keyboard(user_id), parse_mode="HTML")


@flood_guard
async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = "waiting_for_feedback"
    await update.message.reply_text(t(user_id, "feedback_prompt"), reply_markup=cancel_keyboard(user_id))


@flood_guard
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(t(user_id, "stats_admin_only"))
        return
    await update.message.reply_text(
        t(
            user_id,
            "stats_report",
            users=len(stats["users"]),
            hidden=stats["hidden_count"],
            extracted=stats["extracted_count"],
        ),
        parse_mode="HTML",
    )


@flood_guard
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    data = query.data

    if data == CB_HIDE or data == CB_HIDE_AGAIN:
        if get_remaining_quota(user_id) <= 0:
            await safe_edit(query, t(user_id, "limit_reached", limit=DAILY_LIMIT), reply_markup=main_menu_keyboard(user_id))
            return
        reset_user_state(user_id)
        user_states[user_id] = "waiting_for_image_to_hide"
        target = query.message.reply_text if data == CB_HIDE_AGAIN else None
        text = t(user_id, "prompt_send_image_hide")
        if target:
            await target(text, reply_markup=cancel_keyboard(user_id), parse_mode="HTML")
        else:
            await safe_edit(query, text, reply_markup=cancel_keyboard(user_id), parse_mode="HTML")

    elif data == CB_EXTRACT:
        if get_remaining_quota(user_id) <= 0:
            await safe_edit(query, t(user_id, "limit_reached", limit=DAILY_LIMIT), reply_markup=main_menu_keyboard(user_id))
            return
        reset_user_state(user_id)
        user_states[user_id] = "waiting_for_image_to_extract"
        await safe_edit(query, t(user_id, "prompt_send_image_extract"), reply_markup=cancel_keyboard(user_id))

    elif data == CB_HELP:
        await safe_edit(query, t(user_id, "help_text"), reply_markup=back_keyboard(user_id), parse_mode="HTML")

    elif data == CB_ABOUT:
        await safe_edit(query, t(user_id, "about_text"), reply_markup=back_keyboard(user_id), parse_mode="HTML")

    elif data == CB_LANG:
        await safe_edit(query, t(user_id, "choose_lang"), reply_markup=language_keyboard())

    elif data in (CB_LANG_UZ, CB_LANG_RU, CB_LANG_EN):
        lang_map = {CB_LANG_UZ: "uz", CB_LANG_RU: "ru", CB_LANG_EN: "en"}
        user_lang[str(user_id)] = lang_map[data]
        await safe_edit(query, t(user_id, "lang_set"), reply_markup=main_menu_keyboard(user_id))
        await query.message.reply_text(t(user_id, "welcome"), reply_markup=main_menu_keyboard(user_id), parse_mode="HTML")

    elif data == CB_PWD_YES:
        user_states[user_id] = "waiting_for_password_set"
        await safe_edit(query, t(user_id, "ask_password_set"), reply_markup=cancel_keyboard(user_id))

    elif data == CB_PWD_NO:
        user_states[user_id] = "waiting_for_text"
        await safe_edit(query, t(user_id, "prompt_enter_text"), reply_markup=cancel_keyboard(user_id))

    elif data in (CB_CANCEL, CB_BACK):
        reset_user_state(user_id)
        await safe_edit(query, t(user_id, "welcome"), reply_markup=main_menu_keyboard(user_id), parse_mode="HTML")


@flood_guard
async def handle_photo_or_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if state not in ("waiting_for_image_to_hide", "waiting_for_image_to_extract"):
        await update.message.reply_text(t(user_id, "select_from_menu_first"), reply_markup=main_menu_keyboard(user_id))
        return

    if update.message.document:
        file = await update.message.document.get_file()
        compressed_warning = ""
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        compressed_warning = t(user_id, "compressed_warning")
    else:
        await update.message.reply_text(t(user_id, "prompt_send_image_hide"), parse_mode="HTML")
        return

    image_bytes = await file.download_as_bytearray()
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception:
        await update.message.reply_text(t(user_id, "open_image_error"))
        return

    if state == "waiting_for_image_to_hide":
        user_images[user_id] = image
        user_states[user_id] = "waiting_for_password_choice"
        capacity = image_capacity_chars(image)
        width, height = image.size
        info = t(user_id, "capacity_info", w=width, h=height, cap=capacity)
        await update.message.reply_text(f"{info}{compressed_warning}")
        await update.message.reply_text(t(user_id, "ask_password"), reply_markup=password_choice_keyboard(user_id))

    elif state == "waiting_for_image_to_extract":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        status_msg = await update.message.reply_text(f"{t(user_id, 'extracting_status')}\n\n{progress_bar(0)}")
        updater = await make_progress_updater(context, status_msg.chat_id, status_msg.message_id, t(user_id, "extracting_status"))

        try:
            payload = await extract_payload_from_image_progress(image, on_progress=updater)
        except Exception as e:
            logger.error("Extract xatosi: %s", e, exc_info=e)
            payload = None

        if not payload:
            reset_user_state(user_id)
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id, message_id=status_msg.message_id,
                text=t(user_id, "no_hidden_text") + compressed_warning,
            )
            await update.message.reply_text(t(user_id, "choose_from_menu"), reply_markup=main_menu_keyboard(user_id))
            return

        track_extracted()
        register_usage(user_id)

        if payload.startswith(ENC_PREFIX):
            user_pending_payload[user_id] = payload
            user_states[user_id] = "waiting_for_password_check"
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id, message_id=status_msg.message_id,
                text=t(user_id, "ask_password_check"),
            )
        else:
            plain_text = payload[len(PLAIN_PREFIX):] if payload.startswith(PLAIN_PREFIX) else payload
            reset_user_state(user_id)
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id, message_id=status_msg.message_id,
                text=t(user_id, "extracted_prefix", text=plain_text), parse_mode="HTML",
            )
            await update.message.reply_text(t(user_id, "choose_from_menu"), reply_markup=main_menu_keyboard(user_id))


@flood_guard
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)
    message_text = update.message.text

    # --- Fikr-mulohaza ---
    if state == "waiting_for_feedback":
        reset_user_state(user_id)
        username = update.effective_user.username or str(user_id)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"💬 Fikr-mulohaza:\nKimdan: @{username} (ID: {user_id})\n\n{message_text}",
            )
        except Exception as e:
            logger.warning("Adminga feedback yuborilmadi: %s", e)
        await update.message.reply_text(t(user_id, "feedback_thanks"), reply_markup=main_menu_keyboard(user_id))
        return

    # --- Parol o'rnatish (yashirishda) ---
    if state == "waiting_for_password_set":
        user_secret_text[user_id] = json.dumps({"password": message_text})
        user_states[user_id] = "waiting_for_text_with_password"
        await update.message.reply_text(t(user_id, "prompt_enter_text"), reply_markup=cancel_keyboard(user_id))
        return

    # --- Parolni tekshirish (chiqarishda) ---
    if state == "waiting_for_password_check":
        payload = user_pending_payload.get(user_id)
        decrypted = decrypt_payload(payload, message_text) if payload else None
        if decrypted is None:
            await update.message.reply_text(t(user_id, "wrong_password"))
            return
        reset_user_state(user_id)
        await update.message.reply_text(t(user_id, "extracted_prefix", text=decrypted), parse_mode="HTML")
        await update.message.reply_text(t(user_id, "choose_from_menu"), reply_markup=main_menu_keyboard(user_id))
        return

    # --- Matnni yashirish (parolsiz yoki parol bilan) ---
    if state in ("waiting_for_text", "waiting_for_text_with_password"):
        image = user_images.get(user_id)
        if image is None:
            reset_user_state(user_id)
            await update.message.reply_text(t(user_id, "no_image_found"), reply_markup=main_menu_keyboard(user_id))
            return

        if state == "waiting_for_text_with_password":
            pending = user_secret_text.get(user_id)
            password = json.loads(pending)["password"] if pending else None
            payload = encrypt_payload(message_text, password) if password else PLAIN_PREFIX + message_text
        else:
            payload = PLAIN_PREFIX + message_text

        status_msg = await update.message.reply_text(f"{t(user_id, 'hiding_status')}\n\n{progress_bar(0)}")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
        updater = await make_progress_updater(context, status_msg.chat_id, status_msg.message_id, t(user_id, "hiding_status"))

        try:
            result_image = await hide_payload_in_image_progress(image, payload, on_progress=updater)
        except ValueError:
            cap = image_capacity_chars(image)
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id, message_id=status_msg.message_id,
                text=t(user_id, "capacity_exceeded", cap=cap, n=len(payload)),
            )
            return
        except Exception as e:
            logger.error("Hide xatosi: %s", e, exc_info=e)
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id, message_id=status_msg.message_id, text=t(user_id, "unexpected_error"),
            )
            return

        # --- O'z-o'zini tekshirish: natijadan matnni qayta chiqarib, mos kelishini tasdiqlaymiz ---
        await context.bot.edit_message_text(
            chat_id=status_msg.chat_id, message_id=status_msg.message_id, text=t(user_id, "verifying_status"),
        )
        verify_payload = await extract_payload_from_image_progress(result_image)
        if verify_payload != payload:
            logger.error("Tekshiruv muvaffaqiyatsiz: user_id=%s", user_id)
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id, message_id=status_msg.message_id, text=t(user_id, "verify_failed"),
            )
            reset_user_state(user_id)
            return

        buffer = io.BytesIO()
        result_image.save(buffer, format="PNG")
        buffer.seek(0)

        await context.bot.edit_message_text(
            chat_id=status_msg.chat_id, message_id=status_msg.message_id,
            text=f"{t(user_id, 'done')}\n\n{progress_bar(100)}",
        )

        await update.message.reply_document(
            document=InputFile(buffer, filename="stego_result.png"),
            caption=t(user_id, "result_caption"),
            reply_markup=result_keyboard(user_id),
        )

        track_hidden()
        register_usage(user_id)
        reset_user_state(user_id)
        return

    # --- Holat yo'q bo'lsa ---
    await update.message.reply_text(t(user_id, "choose_from_menu"), reply_markup=main_menu_keyboard(user_id))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Xatolik yuz berdi: %s", context.error, exc_info=context.error)


# ============ ASOSIY QISM ============

def main():
    if not BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN muhit o'zgaruvchisi topilmadi! "
            "Railway'da: Project -> Variables -> TELEGRAM_BOT_TOKEN qo'shing."
        )
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo_or_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    if app.job_queue is not None:
        app.job_queue.run_repeating(
            cleanup_stale_sessions, interval=CLEANUP_CHECK_INTERVAL, first=CLEANUP_CHECK_INTERVAL
        )
    else:
        logger.warning(
            "JobQueue mavjud emas — 'pip install \"python-telegram-bot[job-queue]\"' o'rnating, "
            "aks holda eskirgan sessiyalar avtomatik tozalanmaydi."
        )

    logger.info("🤖 Bot ishga tushdi (admin_id=%s, kunlik limit=%s)...", ADMIN_ID, DAILY_LIMIT)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

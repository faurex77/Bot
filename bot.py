"""
Steganografiya Telegram Bot — Railway uchun (v4)
==================================================
Rasm ichiga matn yashiradi va yashirilgan matnni chiqarib beradi.
LSB (Least Significant Bit) usulidan foydalanadi, NumPy bilan tezlashtirilgan.
Tugmali (inline keyboard) menyu va jarayon foizi (progress) bilan boshqariladi.

Railway'ga joylashtirish (deploy):
    1. Ushbu papkani (bot.py, requirements.txt, Procfile) GitHub repo'ga yuklang
       yoki Railway CLI orqali to'g'ridan-to'g'ri deploy qiling.
    2. railway.app'da "New Project" -> "Deploy from GitHub repo" tanlang.
    3. Loyihaning "Variables" bo'limida TELEGRAM_BOT_TOKEN muhit o'zgaruvchisini
       @BotFather'dan olingan token qiymati bilan qo'shing.
    4. Railway avtomatik ravishda Procfile'dagi "worker" jarayonini ishga
       tushiradi — qo'shimcha sozlash shart emas (PORT ochish kerak emas,
       chunki bot webhook emas, polling rejimida ishlaydi).

Lokal (kompyuterda) test qilish:
    pip install -r requirements.txt
    export TELEGRAM_BOT_TOKEN="sizning_tokeningiz"
    python bot.py
"""

import io
import os
import asyncio
import logging
from typing import Dict, Optional

import numpy as np
from PIL import Image
from telegram import (
    Update,
    InputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============ SOZLAMALAR ============
# Railway'da bu qiymat "Variables" bo'limida TELEGRAM_BOT_TOKEN nomi bilan
# o'rnatiladi. Tokenni hech qachon kodga qattiq yozmang (xavfsizlik uchun).
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
END_MARKER = "#####END#####"
PROGRESS_STEPS = 5  # progress necha bosqichda ko'rsatilsin (5 -> 20% dan oshadi)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

user_states: Dict[int, str] = {}
user_images: Dict[int, Image.Image] = {}

CB_HIDE = "menu_hide"
CB_EXTRACT = "menu_extract"
CB_HELP = "menu_help"
CB_ABOUT = "menu_about"
CB_CANCEL = "menu_cancel"
CB_BACK = "menu_back"


# ============ STEGANOGRAFIYA FUNKSIYALARI (NumPy — tez) ============

def _text_to_bits(text: str) -> np.ndarray:
    """Matnni 0/1 uint8 NumPy massiviga o'tkazadi."""
    byte_arr = np.frombuffer(text.encode("utf-8", errors="ignore"), dtype=np.uint8)
    bits = np.unpackbits(byte_arr)
    return bits


def _bits_to_text(bits: np.ndarray) -> str:
    """0/1 bit massivini matnga qaytaradi."""
    n = (len(bits) // 8) * 8
    byte_arr = np.packbits(bits[:n])
    return byte_arr.tobytes().decode("utf-8", errors="ignore")


def image_capacity_chars(image: Image.Image) -> int:
    width, height = image.size
    return (width * height * 3) // 8


async def hide_text_in_image_progress(
    image: Image.Image, secret_text: str, on_progress=None
) -> Image.Image:
    """
    Rasm piksellarining eng kichik bitiga matnni NumPy yordamida (vektorli, tez)
    yashiradi. on_progress(percent) — har bosqichda chaqiriladigan callback.
    """
    image = image.convert("RGB")
    max_capacity = image_capacity_chars(image)
    if len(secret_text) > max_capacity:
        raise ValueError(
            f"Matn juda uzun! Bu rasm maksimal {max_capacity} belgi sig'diradi, "
            f"sizning matningiz {len(secret_text)} belgi."
        )

    if on_progress:
        await on_progress(10)

    arr = np.array(image, dtype=np.uint8)  # (H, W, 3)
    flat = arr.reshape(-1)  # xotira ko'rinishi (view), nusxa emas

    bits = _text_to_bits(secret_text + END_MARKER)
    total_bits = len(bits)

    if on_progress:
        await on_progress(25)

    # Ishni PROGRESS_STEPS bo'lakka bo'lib, har bo'lakdan keyin foizni yangilaymiz
    chunk_size = max(1, -(-total_bits // PROGRESS_STEPS))  # yuqoriga yaxlitlash
    for step in range(PROGRESS_STEPS):
        start = step * chunk_size
        end = min(start + chunk_size, total_bits)
        if start >= end:
            break
        segment = flat[start:end]
        flat[start:end] = (segment & 0xFE) | bits[start:end]
        if on_progress:
            percent = 25 + int(60 * (end / total_bits))
            await on_progress(min(percent, 85))
        await asyncio.sleep(0)  # boshqa so'rovlarga navbat berish

    result_image = Image.fromarray(arr, mode="RGB")

    if on_progress:
        await on_progress(95)

    return result_image


async def extract_text_from_image_progress(
    image: Image.Image, on_progress=None
) -> Optional[str]:
    """Rasm ichidan matnni NumPy yordamida (tez) chiqarib oladi."""
    image = image.convert("RGB")
    arr = np.array(image, dtype=np.uint8)
    flat = arr.reshape(-1)

    if on_progress:
        await on_progress(15)

    total_len = len(flat)
    marker_bits_len = len(_text_to_bits(END_MARKER))

    # END_MARKER'ni topguncha bosqichma-bosqich o'qiymiz (juda katta rasmlarda
    # butun massivni bitta yo'la dekodlash shart emas — bo'lib-bo'lib tekshiramiz).
    search_chunk = max(marker_bits_len * 20, 4096)
    found_text = None
    scanned = 0

    for step in range(PROGRESS_STEPS):
        start = step * (total_len // PROGRESS_STEPS)
        end = total_len if step == PROGRESS_STEPS - 1 else (step + 1) * (total_len // PROGRESS_STEPS)
        if start >= end:
            continue

        bits_chunk = flat[:end] & 1  # boshidan shu yergacha (marker kesilib qolmasligi uchun)
        text_so_far = _bits_to_text(bits_chunk)
        if END_MARKER in text_so_far:
            found_text = text_so_far.split(END_MARKER)[0]
            if on_progress:
                await on_progress(100)
            return found_text

        scanned = end
        if on_progress:
            percent = 15 + int(80 * (end / total_len))
            await on_progress(min(percent, 95))
        await asyncio.sleep(0)

    return None


# ============ TUGMALI MENYULAR ============

def main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔒 Matn yashirish", callback_data=CB_HIDE)],
        [InlineKeyboardButton("🔓 Matnni chiqarish", callback_data=CB_EXTRACT)],
        [
            InlineKeyboardButton("ℹ️ Yordam", callback_data=CB_HELP),
            InlineKeyboardButton("🤖 Bot haqida", callback_data=CB_ABOUT),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Bekor qilish", callback_data=CB_CANCEL)]]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Orqaga", callback_data=CB_BACK)]]
    )


WELCOME_TEXT = (
    "👋 <b>Steganografiya Botiga xush kelibsiz!</b>\n\n"
    "Bu bot rasm ichiga maxfiy matn yashirish va uni qayta chiqarib olish "
    "imkonini beradi (LSB steganografiya usuli).\n\n"
    "Quyidagi tugmalardan birini tanlang:"
)

HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "🔒 <b>Matn yashirish</b> — rasm yuborasiz, so'ng yashirmoqchi bo'lgan "
    "matningizni kiritasiz. Bot sizga yangi PNG rasm qaytaradi.\n\n"
    "🔓 <b>Matnni chiqarish</b> — ichida yashirin matn bo'lgan rasmni yuborasiz, "
    "bot matnni ochib beradi.\n\n"
    "⚠️ <b>Muhim:</b> rasmni Telegram'da <u>fayl</u> sifatida (📎 → File/Document) "
    "yuboring. Oddiy 'rasm' sifatida yuborilsa, Telegram uni siqadi va yashirin "
    "ma'lumot yo'qolib qolishi mumkin."
)

ABOUT_TEXT = (
    "🤖 <b>Bot haqida</b>\n\n"
    "Ushbu bot LSB (Least Significant Bit) steganografiya algoritmidan foydalanadi — "
    "har bir piksel rangining eng kichik bitini o'zgartirib, ko'zga sezilmaydigan "
    "tarzda matn joylaydi. Hisoblashlar NumPy orqali vektorli bajariladi (tez).\n\n"
    "Texnologiya: Python, python-telegram-bot, Pillow, NumPy."
)


# ============ YORDAMCHI: XAVFSIZ TAHRIRLASH ============

async def safe_edit(query, text: str, reply_markup=None, parse_mode=None):
    """
    query.edit_message_text ni xavfsiz chaqiradi.
    Agar asl xabar caption bilan (masalan, fayl) yuborilgan bo'lsa yoki
    boshqa sabab bilan tahrirlab bo'lmasa — yangi xabar yuboradi, dastur qulamaydi.
    """
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest as e:
        logger.info("edit_message_text ishlamadi (%s), yangi xabar yuborilmoqda.", e)
        try:
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            await query.get_bot().send_message(
                chat_id=query.from_user.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )


def progress_bar(percent: int) -> str:
    """Matnli progress-bar hosil qiladi: [██████----] 60%"""
    filled = percent // 10
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {percent}%"


async def make_progress_updater(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, label: str):
    """
    Progress xabarini yangilab turadigan callback yaratadi.
    Telegramning flood-limitidan saqlanish uchun "message is not modified"
    xatoligini e'tiborsiz qoldiradi.
    """
    last_percent = {"value": -1}

    async def update(percent: int):
        percent = max(0, min(100, percent))
        if percent == last_percent["value"]:
            return
        last_percent["value"] = percent
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{label}\n\n{progress_bar(percent)}",
            )
        except BadRequest:
            pass  # "message is not modified" va shu kabi xatolarni e'tiborsiz qoldiramiz

    return update


# ============ HANDLERLAR ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states.pop(user_id, None)
    user_images.pop(user_id, None)
    await update.message.reply_text(
        WELCOME_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP_TEXT, reply_markup=back_keyboard(), parse_mode="HTML"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha inline tugma bosishlarini boshqaradi."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == CB_HIDE:
        user_states[user_id] = "waiting_for_image_to_hide"
        await safe_edit(
            query,
            "📷 Menga rasmni <b>fayl</b> sifatida yuboring (📎 → File/Document, PNG tavsiya etiladi).",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )

    elif query.data == CB_EXTRACT:
        user_states[user_id] = "waiting_for_image_to_extract"
        await safe_edit(
            query,
            "📷 Ichida yashirin matn bo'lgan rasmni yuboring.",
            reply_markup=cancel_keyboard(),
        )

    elif query.data == CB_HELP:
        await safe_edit(query, HELP_TEXT, reply_markup=back_keyboard(), parse_mode="HTML")

    elif query.data == CB_ABOUT:
        await safe_edit(query, ABOUT_TEXT, reply_markup=back_keyboard(), parse_mode="HTML")

    elif query.data in (CB_CANCEL, CB_BACK):
        user_states.pop(user_id, None)
        user_images.pop(user_id, None)
        await safe_edit(query, WELCOME_TEXT, reply_markup=main_menu_keyboard(), parse_mode="HTML")


async def handle_photo_or_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if state not in ("waiting_for_image_to_hide", "waiting_for_image_to_extract"):
        await update.message.reply_text(
            "Iltimos, avval menyudan tanlang:", reply_markup=main_menu_keyboard()
        )
        return

    if update.message.document:
        file = await update.message.document.get_file()
        compressed_warning = ""
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        compressed_warning = (
            "\n\n⚠️ Bu rasm Telegram tomonidan siqilgan bo'lishi mumkin — "
            "keyingi safar fayl (📎 → File) sifatida yuboring."
        )
    else:
        await update.message.reply_text("Iltimos, rasm yuboring.")
        return

    image_bytes = await file.download_as_bytearray()
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception:
        await update.message.reply_text("❌ Rasmni ochib bo'lmadi. Boshqa fayl sinab ko'ring.")
        return

    if state == "waiting_for_image_to_hide":
        user_images[user_id] = image
        user_states[user_id] = "waiting_for_text"
        capacity = image_capacity_chars(image)
        width, height = image.size
        await update.message.reply_text(
            f"✍️ Endi yashirmoqchi bo'lgan matnni yozib yuboring.\n\n"
            f"📐 Rasm: {width}x{height}, taxminan {capacity} belgigacha sig'adi.{compressed_warning}",
            reply_markup=cancel_keyboard(),
        )

    elif state == "waiting_for_image_to_extract":
        status_msg = await update.message.reply_text(f"🔍 Qidirilmoqda...\n\n{progress_bar(0)}")
        updater = await make_progress_updater(
            context, status_msg.chat_id, status_msg.message_id, "🔍 Yashirin matn qidirilmoqda..."
        )

        try:
            extracted = await extract_text_from_image_progress(image, on_progress=updater)
        except Exception as e:
            logger.error("Extract xatosi: %s", e, exc_info=e)
            extracted = None

        user_states.pop(user_id, None)

        if extracted:
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id,
                message_id=status_msg.message_id,
                text=f"🔓 <b>Yashirilgan matn:</b>\n\n{extracted}",
                parse_mode="HTML",
            )
            await update.message.reply_text("Yana nima qilamiz?", reply_markup=main_menu_keyboard())
        else:
            await context.bot.edit_message_text(
                chat_id=status_msg.chat_id,
                message_id=status_msg.message_id,
                text="❌ Bu rasmda yashirin matn topilmadi." + compressed_warning,
            )
            await update.message.reply_text("Yana nima qilamiz?", reply_markup=main_menu_keyboard())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if state != "waiting_for_text":
        await update.message.reply_text(
            "Boshlash uchun menyudan tanlang:", reply_markup=main_menu_keyboard()
        )
        return

    secret_text = update.message.text
    image = user_images.get(user_id)

    if image is None:
        await update.message.reply_text(
            "Xatolik: rasm topilmadi. Qaytadan boshlang.",
            reply_markup=main_menu_keyboard(),
        )
        user_states.pop(user_id, None)
        return

    status_msg = await update.message.reply_text(f"🔒 Yashirilmoqda...\n\n{progress_bar(0)}")
    updater = await make_progress_updater(
        context, status_msg.chat_id, status_msg.message_id, "🔒 Matn rasmga yashirilmoqda..."
    )

    try:
        result_image = await hide_text_in_image_progress(image, secret_text, on_progress=updater)
    except ValueError as e:
        await context.bot.edit_message_text(
            chat_id=status_msg.chat_id, message_id=status_msg.message_id, text=f"❌ {e}"
        )
        return
    except Exception as e:
        logger.error("Hide xatosi: %s", e, exc_info=e)
        await context.bot.edit_message_text(
            chat_id=status_msg.chat_id,
            message_id=status_msg.message_id,
            text="❌ Kutilmagan xatolik yuz berdi. Qaytadan urinib ko'ring.",
        )
        return

    buffer = io.BytesIO()
    result_image.save(buffer, format="PNG")
    buffer.seek(0)

    await context.bot.edit_message_text(
        chat_id=status_msg.chat_id,
        message_id=status_msg.message_id,
        text=f"✅ Tayyor!\n\n{progress_bar(100)}",
    )

    await update.message.reply_document(
        document=InputFile(buffer, filename="stego_result.png"),
        caption="✅ Matn rasmga muvaffaqiyatli yashirildi!\n"
        "Diqqat: faylni PNG holida saqlang, JPEG'ga aylantirmang — aks holda matn yo'qoladi.",
        reply_markup=main_menu_keyboard(),
    )

    user_states.pop(user_id, None)
    user_images.pop(user_id, None)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Kutilmagan xatoliklarni log qiladi (bot qulab tushmasligi uchun)."""
    logger.error("Xatolik yuz berdi: %s", context.error, exc_info=context.error)


# ============ ASOSIY QISM ============

def main():
    if not BOT_TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN muhit o'zgaruvchisi topilmadi! "
            "Railway'da: Project -> Variables -> TELEGRAM_BOT_TOKEN qo'shing. "
            "Lokal ishga tushirishda: export TELEGRAM_BOT_TOKEN=... buyrug'ini bering."
        )
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo_or_document)
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("🤖 Bot ishga tushdi (Railway worker rejimida, polling orqali)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

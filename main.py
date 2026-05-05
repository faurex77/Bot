import os
import telebot
import requests
from flask import Flask, request

# 🔐 ENV
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN:
    raise Exception("BOT_TOKEN topilmadi")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# 🤖 AI FUNCTION
def ask_ai(text):
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "Faqat o‘zbek tilida javob ber"},
                    {"role": "user", "content": text}
                ]
            },
            timeout=20
        )
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print("AI ERROR:", e)
        return "Xatolik, keyinroq urinib ko‘r"

# 🤖 MESSAGE HANDLER
@bot.message_handler(func=lambda m: True)
def handle(message):
    try:
        if not message.text:
            return

        reply = ask_ai(message.text)
        bot.reply_to(message, reply)

    except Exception as e:
        print("BOT ERROR:", e)

# 🌐 WEBHOOK ROUTE
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print("WEBHOOK ERROR:", e)
    return "ok"

# 🧪 TEST ROUTE
@app.route("/")
def home():
    return "Ishlayapti ✅"

# 🚀 START
if __name__ == "__main__":
    import threading
    import time

    # Railway domain olish
    DOMAIN = os.getenv("RAILWAY_STATIC_URL")

    # webhook o‘rnatish
    bot.remove_webhook()
    time.sleep(1)

    if DOMAIN:
        url = f"https://{DOMAIN}/{TOKEN}"
        bot.set_webhook(url=url)
        print("Webhook:", url)
    else:
        print("DOMAIN topilmadi!")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
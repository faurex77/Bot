import os
import telebot
import requests
from flask import Flask, request

# 🔐 ENV
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not API_KEY:
    raise Exception("TOKEN yoki API KEY yo‘q!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# 🌐 DOMAIN (Railway URL)
BASE_URL = os.getenv("RAILWAY_STATIC_URL")
if not BASE_URL:
    BASE_URL = os.getenv("RENDER_EXTERNAL_URL")  # fallback

# 🤖 AI FUNKSIYA
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
                    {
                        "role": "system",
                        "content": "Sen professional AI yordamchisan. Har doim faqat o‘zbek tilida, qisqa, aniq va foydali javob ber. Hech qachon boshqa tilga o‘tma."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                "temperature": 0.7
            },
            timeout=30
        )

        data = r.json()

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            return "AI javob bera olmadi"

    except Exception as e:
        print("AI ERROR:", e)
        return "Xatolik yuz berdi, keyinroq urinib ko‘ring"

# 🤖 BOT HANDLER
@bot.message_handler(func=lambda m: True)
def handle(m):
    try:
        if not m.text:
            return

        reply = ask_ai(m.text)
        bot.reply_to(m, reply)

    except Exception as e:
        print("BOT ERROR:", e)

# 🌐 WEBHOOK ROUTE
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("UTF-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print("WEBHOOK ERROR:", e)
    return "OK"

# 🧪 TEST ROUTE
@app.route("/")
def home():
    return "Bot ishlayapti ✅"

# 🚀 START
if __name__ == "__main__":
    # webhook o‘rnatish
    bot.remove_webhook()

    if BASE_URL:
        WEBHOOK_URL = f"https://{BASE_URL}/{TOKEN}"
        bot.set_webhook(url=WEBHOOK_URL)
        print("Webhook o‘rnatildi:", WEBHOOK_URL)
    else:
        print("DOMAIN topilmadi!")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
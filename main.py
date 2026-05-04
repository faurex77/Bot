import os
import telebot
import requests
import sqlite3
from flask import Flask, request, render_template_string

# 🔐 ENV (Railway dan olinadi)
TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# 📦 DATABASE
db = sqlite3.connect("db.sqlite", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS blocked (id INTEGER PRIMARY KEY)")
db.commit()

# 🤖 AI FUNKSIYA (faqat o‘zbekcha!)
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
                        "content": "Sen professional AI yordamchisan. Har doim faqat o‘zbek tilida, qisqa va tushunarli javob ber."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            }
        )
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "AI vaqtincha ishlamayapti"

# 🤖 BOT
@bot.message_handler(func=lambda m: True)
def handle(m):
    user_id = m.from_user.id

    # block tekshir
    blocked = cursor.execute("SELECT * FROM blocked WHERE id=?", (user_id,)).fetchone()
    if blocked:
        return bot.reply_to(m, "Siz block qilingansiz")

    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    db.commit()

    reply = ask_ai(m.text)
    bot.reply_to(m, reply)

# 🌐 ADMIN PANEL
@app.route("/")
def admin():
    users = cursor.execute("SELECT * FROM users").fetchall()
    blocked = cursor.execute("SELECT * FROM blocked").fetchall()

    return render_template_string("""
    <h1>Admin Panel</h1>
    <p>Foydalanuvchilar: {{users|length}}</p>

    <h3>Block qilish</h3>
    <form method="post" action="/block">
        <input name="id" placeholder="User ID">
        <button>Block</button>
    </form>

    <h3>Blocked users:</h3>
    {% for b in blocked %}
        <p>{{b[0]}}</p>
    {% endfor %}
    """, users=users, blocked=blocked)

@app.route("/block", methods=["POST"])
def block():
    uid = request.form.get("id")
    cursor.execute("INSERT OR IGNORE INTO blocked VALUES (?)", (uid,))
    db.commit()
    return "Block qilindi"

# 🚀 RUN
if __name__ == "__main__":
    import threading

    # bot alohida thread
    threading.Thread(target=bot.polling, kwargs={"none_stop": True}).start()

    # Railway port
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
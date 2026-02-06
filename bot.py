import os
import sqlite3
import telebot
from telebot import types
from datetime import date

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

QUESTIONS_PER_GAME = 10
user_sessions = {}

# ================= DATABASE =================

conn = sqlite3.connect("quiz.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    a TEXT,
    b TEXT,
    c TEXT,
    d TEXT,
    correct TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    total_score INTEGER DEFAULT 0,
    last_play_date TEXT
)
""")

conn.commit()

# ================= HELPERS =================

def get_questions():
    cursor.execute(
        "SELECT * FROM questions ORDER BY RANDOM() LIMIT ?",
        (QUESTIONS_PER_GAME,)
    )
    return cursor.fetchall()

def send_question(chat_id):
    session = user_sessions[chat_id]
    q = session["questions"][session["index"]]

    text = (
        f"❓ {session['index'] + 1}/{QUESTIONS_PER_GAME}\n\n"
        f"{q[1]}\n\n"
        f"A) {q[2]}\n"
        f"B) {q[3]}\n"
        f"C) {q[4]}\n"
        f"D) {q[5]}\n\n"
        "Ответ: A / B / C / D"
    )

    bot.send_message(chat_id, text)

# ================= START =================

@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("▶️ Играть")

    bot.send_message(
        message.chat.id,
        "⚽️ Football Quiz\nГотов сыграть?",
        reply_markup=markup
    )

# ================= PLAY =================

@bot.message_handler(func=lambda m: m.text == "▶️ Играть")
def play(message):
    today = str(date.today())

    cursor.execute(
        "SELECT last_play_date FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    row = cursor.fetchone()

    if row and row[0] == today:
        bot.send_message(message.chat.id, "⛔ Ты уже играл сегодня")
        return

    questions = get_questions()
    if len(questions) < QUESTIONS_PER_GAME:
        bot.send_message(message.chat.id, "⚠️ Недостаточно вопросов")
        return

    user_sessions[message.chat.id] = {
        "questions": questions,
        "index": 0,
        "score": 0
    }

    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (message.from_user.id,)
    )
    cursor.execute(
        "UPDATE users SET last_play_date = ? WHERE telegram_id = ?",
        (today, message.from_user.id)
    )
    conn.commit()

    send_question(message.chat.id)

# ================= ANSWERS =================

@bot.message_handler(func=lambda m: m.text and m.text.upper() in ["A", "B", "C", "D"])
def answer(message):
    chat_id = message.chat.id

    if chat_id not in user_sessions:
        return

    session = user_sessions[chat_id]
    q = session["questions"][session["index"]]

    if message.text.upper() == q[6]:
        session["score"] += 1
        cursor.execute(
            "UPDATE users SET total_score = total_score + 1 WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        conn.commit()

    session["index"] += 1

    if session["index"] >= QUESTIONS_PER_GAME:
        bot.send_message(
            chat_id,
            f"🏁 Игра окончена!\n\n"
            f"Правильных ответов: {session['score']} из {QUESTIONS_PER_GAME}"
        )
        del user_sessions[chat_id]
    else:
        send_question(chat_id)

# ================= RUN =================

print("Bot started")
bot.infinity_polling()

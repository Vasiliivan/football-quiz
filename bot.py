import os
import sqlite3
import telebot
from telebot import types
from datetime import date

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

QUESTIONS_PER_GAME = 10

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

# ================= SESSION STORAGE =================

sessions = {}

# ================= HELPERS =================

def get_questions():
    cursor.execute(
        "SELECT * FROM questions ORDER BY RANDOM() LIMIT ?",
        (QUESTIONS_PER_GAME,)
    )
    return cursor.fetchall()

def send_question(chat_id, user_id):
    session = sessions[user_id]
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
    user_id = message.from_user.id

    if user_id in sessions:
        bot.send_message(message.chat.id, "⛔ Игра уже идёт")
        return

    today = str(date.today())

    cursor.execute(
        "SELECT last_play_date FROM users WHERE telegram_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()

    if row and row[0] == today:
        bot.send_message(message.chat.id, "⛔ Ты уже играл сегодня")
        return

    questions = get_questions()
    if len(questions) < QUESTIONS_PER_GAME:
        bot.send_message(message.chat.id, "⚠️ Недостаточно вопросов")
        return

    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (user_id,)
    )
    cursor.execute(
        "UPDATE users SET last_play_date = ? WHERE telegram_id = ?",
        (today, user_id)
    )
    conn.commit()

    sessions[user_id] = {
        "questions": questions,
        "index": 0,
        "score": 0
    }

    # ❗ УБИРАЕМ клавиатуру
    bot.send_message(
        message.chat.id,
        "🚀 Игра началась!",
        reply_markup=types.ReplyKeyboardRemove()
    )

    send_question(message.chat.id, user_id)

# ================= ANSWERS =================

@bot.message_handler(func=lambda m: m.from_user.id in sessions)
def handle_answer(message):
    user_id = message.from_user.id
    session = sessions[user_id]

    answer = message.text.strip().upper()

    if answer not in ["A", "B", "C", "D"]:
        bot.send_message(message.chat.id, "❗ Введи A, B, C или D")
        return

    q = session["questions"][session["index"]]

    if answer == q[6]:
        session["score"] += 1
        cursor.execute(
            "UPDATE users SET total_score = total_score + 1 WHERE telegram_id = ?",
            (user_id,)
        )
        conn.commit()

    session["index"] += 1

    if session["index"] >= QUESTIONS_PER_GAME:
        bot.send_message(
            message.chat.id,
            f"🏁 Игра окончена!\n\n"
            f"Правильных ответов: {session['score']} из {QUESTIONS_PER_GAME}"
        )
        del sessions[user_id]
        return

    send_question(message.chat.id, user_id)

# ================= RUN =================

print("Bot started")
bot.infinity_polling()

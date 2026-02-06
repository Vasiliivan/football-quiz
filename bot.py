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

# ================= HELPERS =================

def get_questions():
    cursor.execute(
        "SELECT * FROM questions ORDER BY RANDOM() LIMIT ?",
        (QUESTIONS_PER_GAME,)
    )
    return cursor.fetchall()

def ask_question(message, session):
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

    msg = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(msg, handle_answer, session)

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

    session = {
        "questions": questions,
        "index": 0,
        "score": 0,
        "user_id": message.from_user.id
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

    ask_question(message, session)

# ================= ANSWER =================

def handle_answer(message, session):
    answer = message.text.strip().upper()

    if answer not in ["A", "B", "C", "D"]:
        msg = bot.send_message(message.chat.id, "❗ Введи A, B, C или D")
        bot.register_next_step_handler(msg, handle_answer, session)
        return

    q = session["questions"][session["index"]]

    if answer == q[6]:
        session["score"] += 1
        cursor.execute(
            "UPDATE users SET total_score = total_score + 1 WHERE telegram_id = ?",
            (session["user_id"],)
        )
        conn.commit()

    session["index"] += 1

    if session["index"] >= QUESTIONS_PER_GAME:
        bot.send_message(
            message.chat.id,
            f"🏁 Игра окончена!\n\n"
            f"Правильных ответов: {session['score']} из {QUESTIONS_PER_GAME}"
        )
        return

    ask_question(message, session)

# ================= RUN =================

print("Bot started")
bot.infinity_polling()

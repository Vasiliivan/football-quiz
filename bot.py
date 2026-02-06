import os
import sqlite3
import telebot
from telebot import types
from datetime import date

# ================== CONFIG ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

QUESTIONS_PER_GAME = 10

bot = telebot.TeleBot(BOT_TOKEN)

# ================== DATABASE ==================

conn = sqlite3.connect("quiz.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    total_score INTEGER DEFAULT 0,
    last_play_date TEXT
)
""")

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

conn.commit()

# ================== HELPERS ==================

def get_questions(limit):
    cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT ?", (limit,))
    return cursor.fetchall()

def add_user(user_id):
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()

# ================== START ==================

@bot.message_handler(commands=["start"])
def start(message):
    add_user(message.from_user.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("▶️ Играть", "➕ Загрузить вопросы", "🏆 Рейтинг")

    bot.send_message(
        message.chat.id,
        "⚽️ Football Quiz\n\nГотов сыграть?",
        reply_markup=markup
    )

# ================== QUIZ ==================

@bot.message_handler(func=lambda m: m.text == "▶️ Играть")
def play_quiz(message):
    today = str(date.today())

    cursor.execute(
        "SELECT last_play_date FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    row = cursor.fetchone()

    if row and row[0] == today:
        bot.send_message(message.chat.id, "⛔ Ты уже играл сегодня")
        return

    questions = get_questions(QUESTIONS_PER_GAME)

    if len(questions) < QUESTIONS_PER_GAME:
        bot.send_message(message.chat.id, "⚠️ Недостаточно вопросов")
        return

    score = 0

    for index, q in enumerate(questions, start=1):
        text = (
            f"❓ {index}/{QUESTIONS_PER_GAME}\n\n"
            f"{q[1]}\n\n"
            f"A) {q[2]}\n"
            f"B) {q[3]}\n"
            f"C) {q[4]}\n"
            f"D) {q[5]}\n\n"
            "Ответ: A / B / C / D"
        )

        msg = bot.send_message(message.chat.id, text)
        bot.register_next_step_handler(msg, lambda m, c=q[6]: check_answer(m, c))

    cursor.execute(
        "UPDATE users SET last_play_date = ? WHERE telegram_id = ?",
        (today, message.from_user.id)
    )
    conn.commit()

def check_answer(message, correct):
    if message.text and message.text.strip().upper() == correct:
        cursor.execute(
            "UPDATE users SET total_score = total_score + 1 WHERE telegram_id = ?",
            (message.from_user.id,)
        )
        conn.commit()

# ================== LOAD QUESTIONS ==================

@bot.message_handler(func=lambda m: m.text == "➕ Загрузить вопросы")
def ask_file(message):
    bot.send_message(
        message.chat.id,
        "📄 Отправь TXT-файл\n\nФормат:\n"
        "Вопрос\n"
        "A) ...\nB) ...\nC) ...\nD) ...\n"
        "ANSWER: A"
    )

@bot.message_handler(content_types=["document"])
def load_file(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    text = downloaded.decode("utf-8")

    blocks = text.strip().split("\n\n")
    added = 0

    for block in blocks:
        lines = block.split("\n")
        if len(lines) < 6:
            continue

        question = lines[0]
        a = lines[1][3:]
        b = lines[2][3:]
        c = lines[3][3:]
        d = lines[4][3:]
        correct = lines[5].replace("ANSWER:", "").strip().upper()

        cursor.execute(
            "INSERT INTO questions (text, a, b, c, d, correct) VALUES (?, ?, ?, ?, ?, ?)",
            (question, a, b, c, d, correct)
        )
        added += 1

    conn.commit()
    bot.send_message(message.chat.id, f"✅ Загружено вопросов: {added}")

# ================== RATING ==================

@bot.message_handler(func=lambda m: m.text == "🏆 Рейтинг")
def rating(message):
    cursor.execute(
        "SELECT telegram_id, total_score FROM users ORDER BY total_score DESC LIMIT 10"
    )
    rows = cursor.fetchall()

    text = "🏆 Топ игроков:\n\n"
    for i, r in enumerate(rows, start=1):
        text += f"{i}. {r[0]} — {r[1]}\n"

    bot.send_message(message.chat.id, text)

# ================== RUN ==================

print("Bot started")
bot.infinity_polling()

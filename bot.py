import sqlite3
import random
import datetime
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================== НАСТРОЙКИ ==================
TOKEN = os.getenv("BOT_TOKEN")  # Railway ENV
DB_NAME = "quiz.db"

# ================== БАЗА ДАННЫХ ==================
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT,
    a TEXT,
    b TEXT,
    c TEXT,
    d TEXT,
    correct TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_answers (
    user_id INTEGER,
    question_id INTEGER,
    date TEXT
)
""")

conn.commit()

# ================== ВСПОМОГАТЕЛЬНОЕ ==================
def today():
    return datetime.date.today().isoformat()

# ================== КОМАНДЫ ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data="play")]
    ]
    await update.message.reply_text(
        "Привет! Готов сыграть в квиз? 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    cursor.execute("""
    SELECT id, question, a, b, c, d, correct
    FROM questions
    WHERE id NOT IN (
        SELECT question_id FROM user_answers
        WHERE user_id = ? AND date = ?
    )
    ORDER BY RANDOM()
    LIMIT 1
    """, (user_id, today()))

    row = cursor.fetchone()

    if not row:
        await query.edit_message_text(
            "😴 На сегодня вопросы закончились.\nВозвращайся завтра!"
        )
        return

    q_id, question, a, b, c, d, correct = row
    context.user_data["current_question"] = q_id
    context.user_data["correct_answer"] = correct

    keyboard = [
        [InlineKeyboardButton(a, callback_data="a")],
        [InlineKeyboardButton(b, callback_data="b")],
        [InlineKeyboardButton(c, callback_data="c")],
        [InlineKeyboardButton(d, callback_data="d")],
    ]

    await query.edit_message_text(
        f"❓ {question}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_answer = query.data

    q_id = context.user_data.get("current_question")
    correct = context.user_data.get("correct_answer")

    cursor.execute("""
    INSERT INTO user_answers (user_id, question_id, date)
    VALUES (?, ?, ?)
    """, (user_id, q_id, today()))
    conn.commit()

    if user_answer == correct:
        text = "✅ Правильно!"
    else:
        text = f"❌ Неправильно.\nПравильный ответ: {correct.upper()}"

    keyboard = [
        [InlineKeyboardButton("➡️ Следующий вопрос", callback_data="play")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== ЗАПУСК ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(play, pattern="^play$"))
    app.add_handler(CallbackQueryHandler(answer, pattern="^[abcd]$"))

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()

import asyncio
import sqlite3
import os
from datetime import date

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    Message
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- DATABASE ----------

conn = sqlite3.connect("quiz.db")
cursor = conn.cursor()

def init_db():
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

# ---------- KEYBOARD ----------

def main_keyboard():
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="▶️ Играть"))
    kb.add(KeyboardButton(text="🏆 Рейтинг"))
    return kb.adjust(1).as_markup(resize_keyboard=True)

# ---------- HELPERS ----------

def get_questions(limit=10):
    cursor.execute(
        "SELECT * FROM questions ORDER BY RANDOM() LIMIT ?",
        (limit,)
    )
    return cursor.fetchall()

def questions_count():
    cursor.execute("SELECT COUNT(*) FROM questions")
    return cursor.fetchone()[0]

# ---------- COMMANDS ----------

@dp.message(Command("start"))
async def start(message: Message):
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (message.from_user.id,)
    )
    conn.commit()

    await message.answer(
        "⚽️ Привет! Готов сыграть в футбольный квиз?\n\n"
        "📥 Чтобы загрузить вопросы — отправь .txt файл\n"
        "▶️ Нажми «Играть», когда будешь готов",
        reply_markup=main_keyboard()
    )

# ---------- FILE UPLOAD (iPhone supported) ----------

@dp.message(lambda m: m.document is not None)
async def upload_file(message: Message):
    if not message.document.file_name.endswith(".txt"):
        await message.answer("❌ Нужен файл .txt")
        return

    file = await bot.get_file(message.document.file_id)
    file_path = file.file_path

    downloaded = await bot.download_file(file_path)
    text = downloaded.read().decode("utf-8")

    added = 0

    for block in text.split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) != 6:
            continue

        q, a, b, c, d, correct = lines
        correct = correct.strip().upper()

        if correct not in ("A", "B", "C", "D"):
            continue

        cursor.execute(
            "INSERT INTO questions (text, a, b, c, d, correct) VALUES (?, ?, ?, ?, ?, ?)",
            (q, a, b, c, d, correct)
        )
        added += 1

    conn.commit()

    await message.answer(f"✅ Загружено вопросов: {added}")

# ---------- GAME ----------

@dp.message(lambda m: m.text == "▶️ Играть")
async def play(message: Message):
    if questions_count() < 10:
        await message.answer("⚠️ Недостаточно вопросов в базе (нужно минимум 10)")
        return

    today = str(date.today())
    cursor.execute(
        "SELECT last_play_date FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    row = cursor.fetchone()

    if row and row[0] == today:
        await message.answer("⛔️ Ты уже играл сегодня")
        return

    questions = get_questions()
    score = 0

    for q in questions:
        text = (
            f"❓ {q[1]}\n\n"
            f"A) {q[2]}\n"
            f"B) {q[3]}\n"
            f"C) {q[4]}\n"
            f"D) {q[5]}"
        )
        await message.answer(text)

        try:
            answer = await bot.wait_for(
                "message",
                timeout=15,
                check=lambda m: m.from_user.id == message.from_user.id
            )
            if answer.text.strip().upper() == q[6]:
                score += 1
        except asyncio.TimeoutError:
            pass

    cursor.execute(
        "UPDATE users SET total_score = total_score + ?, last_play_date = ? WHERE telegram_id = ?",
        (score, today, message.from_user.id)
    )
    conn.commit()

    await message.answer(f"✅ Готово!\nТвой результат: {score}/10")

# ---------- RATING ----------

@dp.message(lambda m: m.text == "🏆 Рейтинг")
async def rating(message: Message):
    cursor.execute(
        "SELECT telegram_id, total_score FROM users ORDER BY total_score DESC LIMIT 10"
    )
    rows = cursor.fetchall()

    if not rows:
        await message.answer("Рейтинг пока пуст")
        return

    text = "🏆 Топ игроков:\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. {row[1]} очков\n"

    await message.answer(text)

# ---------- MAIN ----------

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

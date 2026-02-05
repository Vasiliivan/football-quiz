import logging
import sqlite3
import os
import random
from datetime import date

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ContentType

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 123456789  # ← ВАЖНО: поставь СВОЙ telegram id

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ====== КНОПКИ ======
kb = ReplyKeyboardMarkup(resize_keyboard=True)
kb.add(KeyboardButton("▶️ Играть"))
kb.add(KeyboardButton("🏆 Рейтинг"))

# ====== БД ======
conn = sqlite3.connect("quiz.db")
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
    score INTEGER DEFAULT 0,
    last_play TEXT
)
""")
conn.commit()


# ====== START ======
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (message.from_user.id,)
    )
    conn.commit()

    await message.answer(
        "⚽️ Привет! Готов сыграть в футбольный квиз?",
        reply_markup=kb
    )


# ====== ЗАГРУЗКА ФАЙЛА ======
@dp.message_handler(content_types=ContentType.DOCUMENT)
async def load_questions(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not message.document.file_name.endswith(".txt"):
        await message.answer("❌ Нужен файл .txt")
        return

    file = await bot.get_file(message.document.file_id)
    await bot.download_file(file.file_path, "questions.txt")

    added = 0

    with open("questions.txt", encoding="utf-8") as f:
        blocks = f.read().strip().split("\n\n")

    for block in blocks:
        lines = block.split("\n")
        if len(lines) != 6:
            continue

        cursor.execute(
            "INSERT INTO questions (text,a,b,c,d,correct) VALUES (?,?,?,?,?,?)",
            (
                lines[0],
                lines[1],
                lines[2],
                lines[3],
                lines[4],
                lines[5].strip().upper()
            )
        )
        added += 1

    conn.commit()
    await message.answer(f"✅ Загружено вопросов: {added}")


# ====== ИГРА ======
@dp.message_handler(lambda m: m.text == "▶️ Играть")
async def play(message: types.Message):
    today = str(date.today())

    cursor.execute(
        "SELECT last_play FROM users WHERE telegram_id=?",
        (message.from_user.id,)
    )
    last = cursor.fetchone()[0]

    if last == today:
        await message.answer("⛔️ Ты уже играл сегодня")
        return

    cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT 10")
    questions = cursor.fetchall()

    if len(questions) < 10:
        await message.answer("⚠️ Недостаточно вопросов в базе")
        return

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
            reply = await bot.wait_for(
                "message",
                timeout=15,
                check=lambda m: m.from_user.id == message.from_user.id
            )
            if reply.text.strip().upper() == q[6]:
                score += 1
        except:
            pass

    cursor.execute(
        "UPDATE users SET score = score + ?, last_play=? WHERE telegram_id=?",
        (score, today, message.from_user.id)
    )
    conn.commit()

    await message.answer(f"✅ Результат: {score}/10")


# ====== РЕЙТИНГ ======
@dp.message_handler(lambda m: m.text == "🏆 Рейтинг")
async def rating(message: types.Message):
    cursor.execute(
        "SELECT telegram_id, score FROM users ORDER BY score DESC LIMIT 10"
    )
    rows = cursor.fetchall()

    text = "🏆 Топ игроков:\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r[0]} — {r[1]}\n"

    await message.answer(text)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

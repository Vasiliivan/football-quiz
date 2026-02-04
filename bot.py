import asyncio
import sqlite3
import random
import os
from datetime import date

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
QUESTIONS_PER_DAY = 10

# ================= BOT =================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= DATABASE =================

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
        username TEXT,
        total_score INTEGER DEFAULT 0,
        last_play_date TEXT
    )
    """)
    conn.commit()


def get_random_questions(limit):
    cursor.execute(
        "SELECT * FROM questions ORDER BY RANDOM() LIMIT ?",
        (limit,)
    )
    return cursor.fetchall()


# ================= STATES =================

class AddQuestion(StatesGroup):
    text = State()
    a = State()
    b = State()
    c = State()
    d = State()
    correct = State()


# ================= START =================

@dp.message(Command("start"))
async def start(message: types.Message):
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
        (message.from_user.id, message.from_user.username)
    )
    conn.commit()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Играть", callback_data="play")],
            [InlineKeyboardButton(text="🏆 Рейтинг", callback_data="rating")]
        ]
    )

    await message.answer(
        "⚽️ Привет! Готов сыграть в футбольный квиз?",
        reply_markup=keyboard
    )


# ================= PLAY =================

@dp.callback_query(F.data == "play")
async def play(callback: types.CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    today = str(date.today())

    cursor.execute(
        "SELECT last_play_date FROM users WHERE telegram_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()

    if row and row[0] == today:
        await callback.message.answer("⛔ Ты уже играл сегодня")
        return

    questions = get_random_questions(QUESTIONS_PER_DAY)

    if len(questions) < QUESTIONS_PER_DAY:
        await callback.message.answer("⚠️ Недостаточно вопросов в базе")
        return

    score = 0

    for q in questions:
        await callback.message.answer(
            f"❓ {q[1]}\n\n"
            f"A) {q[2]}\n"
            f"B) {q[3]}\n"
            f"C) {q[4]}\n"
            f"D) {q[5]}"
        )

        try:
            answer = await bot.wait_for(
                "message",
                timeout=20,
                check=lambda m: m.from_user.id == user_id
            )
            if answer.text.upper() == q[6]:
                score += 1
        except:
            pass

    cursor.execute(
        """
        UPDATE users
        SET total_score = total_score + ?, last_play_date = ?
        WHERE telegram_id = ?
        """,
        (score, today, user_id)
    )
    conn.commit()

    await callback.message.answer(
        f"✅ Квиз завершён!\nРезультат: {score}/{QUESTIONS_PER_DAY}"
    )


# ================= RATING =================

@dp.callback_query(F.data == "rating")
async def rating(callback: types.CallbackQuery):
    await callback.answer()

    cursor.execute(
        "SELECT username, total_score FROM users ORDER BY total_score DESC LIMIT 10"
    )
    rows = cursor.fetchall()

    text = "🏆 Топ игроков:\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. {row[0] or 'Без имени'} — {row[1]}\n"

    await callback.message.answer(text)


# ================= ADD ONE QUESTION =================

@dp.message(Command("add"))
async def add(message: types.Message, state: FSMContext):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return
    await state.set_state(AddQuestion.text)
    await message.answer("Введи текст вопроса")


@dp.message(AddQuestion.text)
async def q_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(AddQuestion.a)
    await message.answer("Вариант A")


@dp.message(AddQuestion.a)
async def q_a(message: types.Message, state: FSMContext):
    await state.update_data(a=message.text)
    await state.set_state(AddQuestion.b)
    await message.answer("Вариант B")


@dp.message(AddQuestion.b)
async def q_b(message: types.Message, state: FSMContext):
    await state.update_data(b=message.text)
    await state.set_state(AddQuestion.c)
    await message.answer("Вариант C")


@dp.message(AddQuestion.c)
async def q_c(message: types.Message, state: FSMContext):
    await state.update_data(c=message.text)
    await state.set_state(AddQuestion.d)
    await message.answer("Вариант D")


@dp.message(AddQuestion.d)
async def q_d(message: types.Message, state: FSMContext):
    await state.update_data(d=message.text)
    await state.set_state(AddQuestion.correct)
    await message.answer("Правильный ответ (A/B/C/D)")


@dp.message(AddQuestion.correct)
async def q_correct(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute(
        "INSERT INTO questions (text,a,b,c,d,correct) VALUES (?,?,?,?,?,?)",
        (data["text"], data["a"], data["b"], data["c"], data["d"], message.text.upper())
    )
    conn.commit()
    await state.clear()
    await message.answer("✅ Вопрос добавлен")


# ================= LOAD QUESTIONS FILE =================

@dp.message(F.content_type == ContentType.DOCUMENT)
async def load_file(message: types.Message):
    if ADMIN_ID and message.from_user.id != ADMIN_ID:
        return

    if not message.document.file_name.endswith(".txt"):
        await message.answer("❌ Нужен .txt файл")
        return

    file = await bot.download(message.document)

    with open(file.name, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    added = 0
    for i in range(0, len(lines), 6):
        try:
            text, a, b, c, d, correct = lines[i:i+6]
            cursor.execute(
                "INSERT INTO questions (text,a,b,c,d,correct) VALUES (?,?,?,?,?,?)",
                (text, a, b, c, d, correct.upper())
            )
            added += 1
        except:
            pass

    conn.commit()
    await message.answer(f"✅ Загружено вопросов: {added}")


# ================= MAIN =================

async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

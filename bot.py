import asyncio
import sqlite3
import random
import os
from datetime import date, datetime, time as dtime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.enums import ParseMode

# ======================
# CONFIG
# ======================

BOT_TOKEN = os.getenv("BOT_TOKEN")

NOTIFY_HOUR = 18
NOTIFY_MINUTE = 0

DB_NAME = "quiz.db"

# ======================
# INIT
# ======================

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# ======================
# DATABASE
# ======================

def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        a TEXT,
        b TEXT,
        c TEXT,
        d TEXT,
        correct TEXT,
        used INTEGER DEFAULT 0
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

def get_random_questions(limit=10):
    cursor.execute(
        "SELECT * FROM questions WHERE used = 0 ORDER BY RANDOM() LIMIT ?",
        (limit,)
    )
    return cursor.fetchall()

def mark_used(ids):
    cursor.executemany(
        "UPDATE questions SET used = 1 WHERE id = ?",
        [(i,) for i in ids]
    )
    conn.commit()

def get_all_users():
    cursor.execute("SELECT telegram_id FROM users")
    return [r[0] for r in cursor.fetchall()]

# ======================
# FSM FOR ADD QUESTION
# ======================

class AddQuestion(StatesGroup):
    text = State()
    a = State()
    b = State()
    c = State()
    d = State()
    correct = State()

# ======================
# COMMANDS
# ======================

@dp.message(Command("start"))
async def start(message: types.Message):
    cursor.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
        (message.from_user.id, message.from_user.username)
    )
    conn.commit()

    await message.answer(
        "⚽ <b>Football Daily Quiz</b>\n\n"
        "👉 /quiz — сыграть\n"
        "🏆 /rating — рейтинг\n"
        "➕ /add_question — добавить вопрос (админ)"
    )

# ======================
# QUIZ
# ======================

@dp.message(Command("quiz"))
async def quiz(message: types.Message):
    today = str(date.today())

    cursor.execute(
        "SELECT last_play_date FROM users WHERE telegram_id = ?",
        (message.from_user.id,)
    )
    row = cursor.fetchone()

    if row and row[0] == today:
        await message.answer("⛔ Ты уже играл сегодня")
        return

    questions = get_random_questions()

    if len(questions) < 10:
        await message.answer("⚠️ Вопросы закончились")
        return

    score = 0
    used_ids = []

    for q in questions:
        used_ids.append(q[0])

        kb = ReplyKeyboardBuilder()
        kb.button(text="A")
        kb.button(text="B")
        kb.button(text="C")
        kb.button(text="D")
        kb.adjust(4)

        await message.answer(
            f"❓ <b>{q[1]}</b>\n\n"
            f"A) {q[2]}\n"
            f"B) {q[3]}\n"
            f"C) {q[4]}\n"
            f"D) {q[5]}",
            reply_markup=kb.as_markup(resize_keyboard=True)
        )

        try:
            answer = await bot.wait_for(
                "message",
                timeout=15
            )
            if answer.text.upper() == q[6]:
                score += 1
        except:
            pass

    mark_used(used_ids)

    cursor.execute(
        "UPDATE users SET total_score = total_score + ?, last_play_date = ? WHERE telegram_id = ?",
        (score, today, message.from_user.id)
    )
    conn.commit()

    await message.answer(
        f"✅ Викторина окончена!\n"
        f"Твой результат: <b>{score}/10</b>",
        reply_markup=types.ReplyKeyboardRemove()
    )

# ======================
# RATING
# ======================

@dp.message(Command("rating"))
async def rating(message: types.Message):
    cursor.execute(
        "SELECT username, total_score FROM users ORDER BY total_score DESC LIMIT 10"
    )
    rows = cursor.fetchall()

    text = "🏆 <b>Топ игроков</b>\n\n"
    for i, (name, score) in enumerate(rows, 1):
        text += f"{i}. {name or 'Без имени'} — {score}\n"

    await message.answer(text)

# ======================
# ADD QUESTION
# ======================

@dp.message(Command("add_question"))
async def add_question(message: types.Message, state: FSMContext):
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
        "INSERT INTO questions (text, a, b, c, d, correct) VALUES (?, ?, ?, ?, ?, ?)",
        (data["text"], data["a"], data["b"], data["c"], data["d"], message.text.upper())
    )
    conn.commit()

    await state.clear()
    await message.answer("✅ Вопрос добавлен")

# ======================
# DAILY NOTIFY
# ======================

async def daily_notify():
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), dtime(NOTIFY_HOUR, NOTIFY_MINUTE))

        if now >= target:
            target = target.replace(day=now.day + 1)

        await asyncio.sleep((target - now).seconds)

        for uid in get_all_users():
            try:
                await bot.send_message(uid, "⚽ Сегодня доступна новая викторина!\n👉 /quiz")
            except:
                pass

# ======================
# MAIN
# ======================

async def main():
    init_db()
    asyncio.create_task(daily_notify())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

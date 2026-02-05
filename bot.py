import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

MAX_QUESTIONS = 10

# user_id -> session
user_sessions = {}


def parse_questions(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


async def send_next_question(message: Message, user_id: int):
    session = user_sessions[user_id]

    # ✅ ЖЁСТКИЙ СТОП
    if session["current"] >= MAX_QUESTIONS:
        await message.answer(
            f"🏁 Игра окончена!\n"
            f"Вы ответили на {MAX_QUESTIONS} вопросов."
        )
        del user_sessions[user_id]
        return

    question = session["questions"][session["current"]]
    session["current"] += 1

    await message.answer(
        f"❓ Вопрос {session['current']} из {MAX_QUESTIONS}:\n\n{question}"
    )


@dp.message(Command("start"))
async def start(message: Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text="▶️ Начать игру")
    kb.button(text="📄 Загрузить вопросы")
    kb.adjust(1)

    await message.answer(
        "Привет! 👋\n"
        "Квиз-бот.\n"
        "Игра всегда состоит из 10 вопросов.",
        reply_markup=kb.as_markup(resize_keyboard=True),
    )


@dp.message(F.content_type == ContentType.DOCUMENT)
async def handle_file(message: Message):
    if not message.document.file_name.endswith(".txt"):
        await message.answer("❌ Нужен файл .txt")
        return

    file = await bot.get_file(message.document.file_id)
    content = await bot.download_file(file.file_path)
    text = content.read().decode("utf-8")

    questions = parse_questions(text)

    if len(questions) < MAX_QUESTIONS:
        await message.answer(
            f"❌ В файле только {len(questions)} вопросов.\n"
            f"Нужно минимум {MAX_QUESTIONS}."
        )
        return

    user_sessions[message.from_user.id] = {
        "questions": questions,
        "current": 0,
    }

    await message.answer("✅ Вопросы загружены. Начинаем игру!")
    await send_next_question(message, message.from_user.id)


@dp.message(F.text == "▶️ Начать игру")
async def start_game(message: Message):
    try:
        with open("questions.txt", "r", encoding="utf-8") as f:
            questions = parse_questions(f.read())
    except FileNotFoundError:
        await message.answer("❌ Файл questions.txt не найден")
        return

    if len(questions) < MAX_QUESTIONS:
        await message.answer("❌ В questions.txt меньше 10 вопросов")
        return

    user_sessions[message.from_user.id] = {
        "questions": questions,
        "current": 0,
    }

    await message.answer("🎮 Игра началась!")
    await send_next_question(message, message.from_user.id)


@dp.message(F.text)
async def handle_answer(message: Message):
    user_id = message.from_user.id

    if user_id not in user_sessions:
        return

    await send_next_question(message, user_id)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

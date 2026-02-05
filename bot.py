import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ContentType

from config import BOT_TOKEN
from storage import get_user
from keyboards import main_menu
from questions import parse_questions
from quiz import send_question, handle_answer

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    user = get_user(message.from_user.id)
    await message.answer(
        "⚽ Футбольный квиз\n\n"
        "📥 Отправь .txt файл\n"
        "▶️ Нажми Играть",
        reply_markup=main_menu()
    )

@dp.message(F.content_type == ContentType.DOCUMENT)
async def upload_questions(message: Message):
    user = get_user(message.from_user.id)

    if not message.document.file_name.endswith(".txt"):
        await message.answer("❌ Нужен .txt файл")
        return

    file = await bot.download(message.document)
    text = file.read().decode("utf-8")

    user["questions"] = parse_questions(text)
    user["index"] = 0
    user["score"] = 0

    await message.answer(f"✅ Загружено: {len(user['questions'])} вопросов")

@dp.message(F.text == "▶️ Играть")
async def play(message: Message):
    user = get_user(message.from_user.id)
    user["active"] = True
    await send_question(message, user)

@dp.message(F.text.in_(["A", "B", "C", "D"]))
async def answer(message: Message):
    user = get_user(message.from_user.id)
    if not user["active"]:
        return
    await handle_answer(message, user)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

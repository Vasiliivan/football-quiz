import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

MENU = ReplyKeyboardMarkup(
    [["▶️ Играть", "🏆 Рейтинг"]],
    resize_keyboard=True
)

users = {}
ratings = {}


def parse_questions(text: str):
    blocks = text.strip().split("\n\n")
    questions = []

    for block in blocks:
        lines = block.split("\n")
        if len(lines) < 6:
            continue

        question = lines[0]
        options = lines[1:5]
        answer = lines[5].replace("ANSWER:", "").strip().upper()

        questions.append({
            "q": question,
            "opts": options,
            "a": answer
        })

    return questions


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Готов сыграть в футбольный квиз?\n\n"
        "📄 Чтобы загрузить вопросы — отправь .txt файл\n"
        "▶️ Нажми «Играть», когда будешь готов",
        reply_markup=MENU
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Нужен файл .txt")
        return

    file = await doc.get_file()
    content = await file.download_as_bytearray()
    text = content.decode("utf-8")

    questions = parse_questions(text)
    if not questions:
        await update.message.reply_text("❌ Не удалось прочитать вопросы")
        return

    user_id = update.effective_user.id
    users[user_id] = {
        "questions": questions,
        "index": 0,
        "score": 0,
        "active": False
    }

    await update.message.reply_text(
        f"✅ Загружено вопросов: {len(questions)}\nНажми ▶️ Играть",
        reply_markup=MENU
    )


async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text(
            "📄 Сначала загрузи файл с вопросами"
        )
        return

    users[user_id]["index"] = 0
    users[user_id]["score"] = 0
    users[user_id]["active"] = True

    await send_question(update, context)


async def send_question(update, context):
    user_id = update.effective_user.id
    user = users[user_id]

    if user["index"] >= len(user["questions"]):
        score = user["score"]
        ratings[user_id] = max(ratings.get(user_id, 0), score)

        user["active"] = False

        await update.message.reply_text(
            f"🏁 Игра окончена!\n🎯 Твой счёт: {score}",
            reply_markup=MENU
        )
        return

    q = user["questions"][user["index"]]

    text = (
        f"❓ {q['q']}\n\n"
        f"{q['opts'][0]}\n"
        f"{q['opts'][1]}\n"
        f"{q['opts'][2]}\n"
        f"{q['opts'][3]}"
    )

    await update.message.reply_text(text)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()

    if user_id not in users:
        return

    user = users[user_id]
    if not user["active"]:
        return

    if text not in ["A", "B", "C", "D"]:
        return

    correct = user["questions"][user["index"]]["a"]
    if text == correct:
        user["score"] += 1
        await update.message.reply_text("✅ Верно!")
    else:
        await update.message.reply_text(f"❌ Неверно! Правильный ответ: {correct}")

    user["index"] += 1
    await send_question(update, context)


async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ratings:
        await update.message.reply_text("📭 Рейтинг пуст")
        return

    text = "🏆 Рейтинг:\n\n"
    for i, (uid, score) in enumerate(
        sorted(ratings.items(), key=lambda x: x[1], reverse=True),
        start=1
    ):
        text += f"{i}. {score} очков\n"

    await update.message.reply_text(text)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.Regex("^▶️ Играть$"), play))
    app.add_handler(MessageHandler(filters.Regex("^🏆 Рейтинг$"), rating))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    app.run_polling()


if __name__ == "__main__":
    main()

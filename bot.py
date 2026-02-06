import telebot
from telebot import types
import os
import random


bot = telebot.TeleBot(BOT_TOKEN)

# Храним данные пользователей
user_data = {}

QUESTIONS_LIMIT = 10


# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------

def parse_questions(file_path):
    questions = []

    with open(file_path, "r", encoding="utf-8") as f:
        blocks = f.read().strip().split("\n\n")

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 6:
            continue

        question_text = lines[0]
        options = lines[1:5]
        answer_line = lines[5]

        if not answer_line.upper().startswith("ANSWER:"):
            continue

        answer = answer_line.split(":")[1].strip().upper()

        questions.append({
            "text": question_text,
            "options": options,
            "answer": answer
        })

    return questions


def send_question(chat_id, user_id):
    data = user_data[user_id]
    q = data["questions"][data["current"]]

    text = f"❓ {q['text']}\n\n"
    for opt in q["options"]:
        text += opt + "\n"

    bot.send_message(chat_id, text)


def finish_game(chat_id, user_id):
    score = user_data[user_id]["score"]
    bot.send_message(
        chat_id,
        f"🏁 Игра окончена!\n\n"
        f"Твой результат: {score} из {QUESTIONS_LIMIT}\n\n"
        f"Нажми /start, чтобы сыграть снова"
    )
    del user_data[user_id]


# ---------- ХЭНДЛЕРЫ ----------

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id

    user_data[user_id] = {
        "questions": [],
        "current": 0,
        "score": 0
    }

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("▶️ Играть")

    bot.send_message(
        message.chat.id,
        "⚽ Привет! Готов сыграть в футбольный квиз?\n\n"
        "📎 Отправь .txt файл с вопросами\n"
        "▶️ Нажми «Играть», когда будешь готов",
        reply_markup=keyboard
    )


@bot.message_handler(content_types=["document"])
def handle_file(message):
    user_id = message.from_user.id

    if not message.document.file_name.endswith(".txt"):
        bot.send_message(message.chat.id, "❌ Нужен файл .txt")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    os.makedirs("files", exist_ok=True)
    path = f"files/{user_id}_questions.txt"

    with open(path, "wb") as f:
        f.write(downloaded)

    questions = parse_questions(path)

    if len(questions) < QUESTIONS_LIMIT:
        bot.send_message(
            message.chat.id,
            f"❌ В файле должно быть минимум {QUESTIONS_LIMIT} вопросов"
        )
        return

    random.shuffle(questions)

    user_data[user_id]["questions"] = questions

    bot.send_message(
        message.chat.id,
        f"✅ Вопросы загружены: {len(questions)}"
    )


@bot.message_handler(func=lambda m: m.text == "▶️ Играть")
def play(message):
    user_id = message.from_user.id

    if user_id not in user_data or not user_data[user_id]["questions"]:
        bot.send_message(message.chat.id, "❗ Сначала загрузи файл с вопросами")
        return

    user_data[user_id]["current"] = 0
    user_data[user_id]["score"] = 0

    send_question(message.chat.id, user_id)


@bot.message_handler(func=lambda m: m.text and m.text.upper() in ["A", "B", "C", "D"])
def answer(message):
    user_id = message.from_user.id

    if user_id not in user_data:
        bot.send_message(message.chat.id, "❗ Нажми /start")
        return

    data = user_data[user_id]

    # если игра уже закончена
    if data["current"] >= QUESTIONS_LIMIT:
        finish_game(message.chat.id, user_id)
        return

    q = data["questions"][data["current"]]
    correct = q["answer"]

    if message.text.upper() == correct:
        data["score"] += 1
        bot.send_message(message.chat.id, "✅ Верно!")
    else:
        bot.send_message(
            message.chat.id,
            f"❌ Неверно! Правильный ответ: {correct}"
        )

    data["current"] += 1

    # 🔴 СТРОГАЯ ОСТАНОВКА ПОСЛЕ 10
    if data["current"] >= QUESTIONS_LIMIT:
        finish_game(message.chat.id, user_id)
        return

    send_question(message.chat.id, user_id)


# ---------- ЗАПУСК ----------

print("Bot started")
bot.infinity_polling()

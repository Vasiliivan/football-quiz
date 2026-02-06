import os
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
QUESTIONS_LIMIT = 10

bot = telebot.TeleBot(BOT_TOKEN)

questions = []
user_state = {}


# === ЗАГРУЗКА ВОПРОСОВ ===
def load_questions_from_file(path):
    loaded = []

    with open(path, "r", encoding="utf-8") as f:
        block = []

        for line in f:
            line = line.strip()

            if not line:
                if block:
                    loaded.append(block)
                    block = []
            else:
                block.append(line)

        if block:
            loaded.append(block)

    return loaded


# === ДОСТАТЬ БУКВУ ОТВЕТА ===
def extract_answer(answer_line):
    answer_line = answer_line.upper()

    if "A" in answer_line:
        return "A"
    if "B" in answer_line:
        return "B"
    if "C" in answer_line:
        return "C"
    if "D" in answer_line:
        return "D"

    return ""


# === КЛАВИАТУРА ===
def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("▶️ Играть", "📂 Загрузить")
    kb.add("🏆 Рейтинг")
    return kb


# === START ===
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "⚽ Football Quiz\n\nГотов сыграть?",
        reply_markup=main_keyboard()
    )


# === ЗАГРУЗКА ФАЙЛА ===
@bot.message_handler(content_types=["document"])
def handle_file(message):
    global questions

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    path = "questions.txt"
    with open(path, "wb") as f:
        f.write(downloaded)

    questions = load_questions_from_file(path)

    bot.send_message(
        message.chat.id,
        f"✅ Загружено вопросов: {len(questions)}",
        reply_markup=main_keyboard()
    )


# === НАЧАТЬ ИГРУ ===
@bot.message_handler(func=lambda m: m.text == "▶️ Играть")
def play(message):
    if not questions:
        bot.send_message(message.chat.id, "❌ Сначала загрузите вопросы")
        return

    user_state[message.chat.id] = {
        "index": 0,
        "score": 0,
        "active": True
    }

    send_question(message.chat.id)


# === ОТПРАВКА ВОПРОСА ===
def send_question(chat_id):
    state = user_state.get(chat_id)

    if not state or not state["active"]:
        return

    idx = state["index"]

    if idx >= QUESTIONS_LIMIT or idx >= len(questions):
        bot.send_message(
            chat_id,
            f"🏁 Игра окончена!\nПравильных ответов: {state['score']} из {QUESTIONS_LIMIT}",
            reply_markup=main_keyboard()
        )
        state["active"] = False
        return

    q = questions[idx]

    text = f"❓ {idx+1}/{QUESTIONS_LIMIT}\n\n" + "\n".join(q[:-1]) + "\n\nОтвет: A / B / C / D"

    bot.send_message(chat_id, text)


# === ОТВЕТ ПОЛЬЗОВАТЕЛЯ ===
@bot.message_handler(func=lambda m: m.text and m.text.upper() in ["A", "B", "C", "D"])
def answer(message):
    state = user_state.get(message.chat.id)

    if not state or not state["active"]:
        return

    q = questions[state["index"]]

    correct = extract_answer(q[-1])

    if message.text.upper() == correct:
        state["score"] += 1
        bot.send_message(message.chat.id, "✅ Верно!")
    else:
        bot.send_message(
            message.chat.id,
            f"❌ Неверно! Правильный ответ: {correct}"
        )

    state["index"] += 1
    send_question(message.chat.id)


# === РЕЙТИНГ ===
@bot.message_handler(func=lambda m: m.text == "🏆 Рейтинг")
def rating(message):
    bot.send_message(message.chat.id, "🏆 Рейтинг будет позже 😉")


print("Bot started")
bot.infinity_polling(skip_pending=True)

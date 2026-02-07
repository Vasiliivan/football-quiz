import os
import json
import random
import time
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")

QUESTIONS_LIMIT = 10
COOLDOWN = 24 * 60 * 60  # 24 часа

bot = telebot.TeleBot(BOT_TOKEN)

questions = []
user_state = {}
USERS_FILE = "users.json"


# ================== USERS STORAGE ==================
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


users = load_users()


# ================== QUESTIONS ==================
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


def extract_answer(line):
    line = line.upper()
    for c in ["A", "B", "C", "D"]:
        if c in line:
            return c
    return ""


# ================== KEYBOARD ==================
def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("▶️ Играть")
    kb.add("🏆 Рейтинг")
    kb.add("📂 Загрузить")
    return kb


# ================== START ==================
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "⚽ Football Daily Quiz\n\nОдин шанс в день. Готов?",
        reply_markup=main_keyboard()
    )


# ================== FILE UPLOAD ==================
@bot.message_handler(content_types=["document"])
def handle_file(message):
    global questions

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    with open("questions.txt", "wb") as f:
        f.write(downloaded)

    questions = load_questions_from_file("questions.txt")
    random.shuffle(questions)

    bot.send_message(
        message.chat.id,
        f"✅ Загружено вопросов: {len(questions)}",
        reply_markup=main_keyboard()
    )


# ================== PLAY ==================
@bot.message_handler(func=lambda m: m.text == "▶️ Играть")
def play(message):
    uid = str(message.from_user.id)
    now = int(time.time())

    if uid in users and now - users[uid]["last_play"] < COOLDOWN:
        left = COOLDOWN - (now - users[uid]["last_play"])
        hours = left // 3600
        minutes = (left % 3600) // 60
        bot.send_message(
            message.chat.id,
            f"⏳ Ты уже играл сегодня\nПопробуй через {hours}ч {minutes}м"
        )
        return

    if len(questions) < QUESTIONS_LIMIT:
        bot.send_message(message.chat.id, "❌ Недостаточно вопросов")
        return

    game_questions = random.sample(questions, QUESTIONS_LIMIT)

    user_state[message.chat.id] = {
        "index": 0,
        "score": 0,
        "questions": game_questions,
        "active": True
    }

    users.setdefault(uid, {
        "name": message.from_user.first_name,
        "score": 0,
        "games": 0,
        "last_play": 0
    })

    send_question(message.chat.id)


# ================== SEND QUESTION ==================
def send_question(chat_id):
    state = user_state.get(chat_id)
    if not state or not state["active"]:
        return

    idx = state["index"]

    if idx >= QUESTIONS_LIMIT:
        finish_game(chat_id)
        return

    q = state["questions"][idx]
    text = f"❓ {idx+1}/{QUESTIONS_LIMIT}\n\n" + "\n".join(q[:-1]) + "\n\nОтвет: A / B / C / D"
    bot.send_message(chat_id, text)


# ================== ANSWER ==================
@bot.message_handler(func=lambda m: m.text and m.text.upper() in ["A", "B", "C", "D"])
def answer(message):
    state = user_state.get(message.chat.id)
    if not state or not state["active"]:
        return

    q = state["questions"][state["index"]]
    correct = extract_answer(q[-1])

    if message.text.upper() == correct:
        state["score"] += 1
        bot.send_message(message.chat.id, "✅ Верно!")
    else:
        bot.send_message(message.chat.id, f"❌ Неверно! Правильный ответ: {correct}")

    state["index"] += 1
    send_question(message.chat.id)


# ================== FINISH ==================
def finish_game(chat_id):
    state = user_state[chat_id]
    uid = str(bot.get_chat(chat_id).id)

    users[uid]["score"] += state["score"]
    users[uid]["games"] += 1
    users[uid]["last_play"] = int(time.time())
    save_users(users)

    bot.send_message(
        chat_id,
        f"🏁 Игра окончена!\n"
        f"Правильных ответов: {state['score']} из {QUESTIONS_LIMIT}",
        reply_markup=main_keyboard()
    )

    state["active"] = False


# ================== RATING ==================
@bot.message_handler(func=lambda m: m.text == "🏆 Рейтинг")
def rating(message):
    if not users:
        bot.send_message(message.chat.id, "Рейтинг пуст")
        return

    top = sorted(users.values(), key=lambda x: x["score"], reverse=True)[:10]

    text = "🏆 Топ-10 игроков:\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {u['name']} — {u['score']} очков ({u['games']} игр)\n"

    bot.send_message(message.chat.id, text)


print("Bot started")
bot.infinity_polling(skip_pending=True)

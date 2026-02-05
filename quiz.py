from keyboards import answer_keyboard

async def send_question(message, user):
    if user["index"] >= len(user["questions"]):
        await message.answer(
            f"🏁 Конец!\n"
            f"Результат: {user['score']} / {len(user['questions'])}"
        )
        user["active"] = False
        return

    q = user["questions"][user["index"]]

    text = f"❓ {q['question']}\n\n"
    text += "\n".join(
        f"{chr(65+i)}) {opt}" for i, opt in enumerate(q["options"])
    )

    await message.answer(text, reply_markup=answer_keyboard())

async def handle_answer(message, user):
    q = user["questions"][user["index"]]

    if message.text.upper() == q["answer"]:
        user["score"] += 1
        await message.answer("✅ Верно")
    else:
        await message.answer(f"❌ Неверно. Ответ: {q['answer']}")

    user["index"] += 1
    await send_question(message, user)

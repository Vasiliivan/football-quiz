from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="▶️ Играть")]],
        resize_keyboard=True
    )

def answer_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="A"), KeyboardButton(text="B")],
            [KeyboardButton(text="C"), KeyboardButton(text="D")]
        ],
        resize_keyboard=True
    )

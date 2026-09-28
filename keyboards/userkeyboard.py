from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def user_rows(with_training: bool = False) -> list:
    """Основные кнопки пользователя (3×3). Кнопка «Обучение» появится вместе с разделом."""
    middle = [KeyboardButton(text='Матч-штрафы')]
    if with_training:
        middle.append(KeyboardButton(text='Обучение'))
    middle.append(KeyboardButton(text='Награды'))
    return [
        [KeyboardButton(text='Личный кабинет'), KeyboardButton(text='Правила'), KeyboardButton(text='🔍 Поиск')],
        middle,
        [KeyboardButton(text='Список танков'), KeyboardButton(text='Список сражений'), KeyboardButton(text='Список ивентов')],
    ]


userboard = ReplyKeyboardMarkup(keyboard=user_rows(with_training=True), resize_keyboard=True)

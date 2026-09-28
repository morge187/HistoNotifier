from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from .userkeyboard import user_rows

ADMIN_ROWS = [
    [KeyboardButton(text='Добавить ивент'), KeyboardButton(text='Редактировать ивент'), KeyboardButton(text='Удалить ивент')],
    [KeyboardButton(text='Добавить награду'), KeyboardButton(text='Изменить награду'), KeyboardButton(text='Удалить награду')],
    [KeyboardButton(text='Добавить танк'), KeyboardButton(text='Изменить танк'), KeyboardButton(text='Удалить танк')],
    [KeyboardButton(text='Добавить сражение'), KeyboardButton(text='Изменить сражение'), KeyboardButton(text='Удалить сражение')],
    [KeyboardButton(text='Тесты ⚙️')],
]

adminboard = ReplyKeyboardMarkup(keyboard=user_rows(with_training=True) + ADMIN_ROWS, resize_keyboard=True)

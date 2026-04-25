from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

adminboard = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text='Мои кадры'),
        KeyboardButton(text='Правила'),
        KeyboardButton(text='матч-штрафы')
    ],
    [
        KeyboardButton(text='Поменять имя'),
        KeyboardButton(text='Мои награды'),
        KeyboardButton(text='Список наград')
    ],
    [
        KeyboardButton(text='Список ивентов'),
        KeyboardButton(text='Список танков'),
    ],
    [
        KeyboardButton(text='Добавить ивент'),
        KeyboardButton(text='Редактировать ивент'),
        KeyboardButton(text='Удалить ивент'),
    ],
    [
        KeyboardButton(text='Добавить награду'),
        KeyboardButton(text='Изменить награду'),
        KeyboardButton(text='Удалить награду')
    ],
    [
        KeyboardButton(text='Добавить танк'),
        KeyboardButton(text='Изменить танк'),
        KeyboardButton(text='Удалить танк'),
    ],
    [
        KeyboardButton(text='Список сражений'),
        KeyboardButton(text='Добавить сражение'),
    ],
    [
        KeyboardButton(text='Изменить сражение'),
        KeyboardButton(text='Удалить сражение'),
    ]
], resize_keyboard=True)
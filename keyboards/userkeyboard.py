from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

userboard = ReplyKeyboardMarkup(keyboard=[
    [
        KeyboardButton(text='Список наград'),
        KeyboardButton(text='Мои кадры'),
        KeyboardButton(text='Правила')
    ],
    [
        KeyboardButton(text='Поменять имя'),
        KeyboardButton(text='Мои награды')
    ],
    [
        KeyboardButton(text='Список ивентов'),
        KeyboardButton(text='Список танков'),
        KeyboardButton(text='матч-штрафы')
    ]
], resize_keyboard=True)
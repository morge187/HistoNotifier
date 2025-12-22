import os
from dotenv import load_dotenv
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database.requests import set_status

admin_create = Router()

load_dotenv()

PASSWORD = os.getenv("PASSWORD")
print(PASSWORD)

class adminIs(StatesGroup):
    password = State()


@admin_create.message(Command('admin'))
async def start_time(message: Message, state: FSMContext):
    await message.answer('Введи пароль')
    await state.set_state(adminIs.password)

@admin_create.message(adminIs.password)
async def is_correcr(message: Message, state: FSMContext):
    await state.update_data(password=message.text)
    if (message.text == PASSWORD):
        await set_status(message.from_user.id, 'admin')
        await message.answer('Всё верно')
    else:
        await message.answer('Неверный пароль')
    await state.clear()
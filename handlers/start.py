from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram import Router
from keyboards.userkb import user_key_board
from keyboards.userin import babax
from database.requests import set_user, set_status

start = Router()

@start.message(CommandStart())
async def start_command(message: Message):
    await set_user(message.from_user.id)
    await message.answer('сообщение', reply_markup=babax)
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram import Router
from keyboards.userkb import user_key_board
from keyboards.userin import babax

start = Router()

@start.message(CommandStart())
async def start_command(message: Message):
    await message.answer('сообщение', reply_markup=babax)
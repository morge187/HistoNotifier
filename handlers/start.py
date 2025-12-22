from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram import Router
from aiogram import F
from keyboards import userboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database.requests import set_user, set_status, set_name_user, get_user

start = Router()

class Name(StatesGroup):
    name = State()

@start.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await set_user(message.from_user.id)
     # создать юзера
    data = await get_user(message.from_user.id)
    if data.name != None:
        return
    
    await set_status(message.from_user.id, 'base_user') # задать статут обчного юзера
    await message.answer('Тебя приветсивует HistoNotifier бот, напиши сой ник')
    await state.set_state(Name.name)

@start.message(Command("rename"))
@start.message(F.text == 'Поменять имя')
async def chacge_name(message: Message, state: FSMContext):
    await message.answer('Напиши сой ник')
    await state.set_state(Name.name)

@start.message(Name.name)
async def set_name_to_user(message: Message, state: FSMContext):
    await set_name_user(message.from_user.id, message.text)
    await message.answer('Ваш ник успешно сохранён', reply_markup=userboard)
    await state.clear()
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram import Router
from aiogram import F
from keyboards import userboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database.requests import set_user, set_status, set_name_user, get_user

start = Router()

array_exchange = ["отмена", "Отмена", "Cancel", "cancel", "Стоп"]

class Name(StatesGroup):
    name = State()
    nothing = State()

@start.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await set_user(message.from_user.id)
     # создать юзера
    data = await get_user(message.from_user.id)
    if data.name != None:
        return
    
    await set_status(message.from_user.id, 'base_user') # задать статут обчного юзера
    await message.answer('Тебя приветсивует HistoNotifier бот, напиши свой ник')
    await state.set_state(Name.name)

@start.message(Command("rename"))
@start.message(F.text == 'Поменять имя')
async def chacge_name(message: Message, state: FSMContext):
    await message.answer('Напиши свой ник')
    await state.set_state(Name.name)

@start.message(Name.name)
async def set_name_to_user(message: Message, state: FSMContext):
    new_nick = message.text.strip()
    
    # Проверка на пустой ник
    if not new_nick or len(new_nick) < 2:
        await message.answer('Ник должен содержать минимум 2 символа. Попробуй ещё раз:')
        return
    
    # Проверка на уникальность ника
    from database.requests import check_name_exists
    name_taken = await check_name_exists(new_nick)
    
    if name_taken:
        await message.answer(f'❌ Ник "{new_nick}" уже занят. Выбери другой:')
        return
    
    # Ник уникален
    await set_name_user(message.from_user.id, new_nick)
    await message.answer(f'✅ Ваш ник "{new_nick}" успешно сохранён', reply_markup=userboard)
    await state.clear()

@start.message(F.text.in_(array_exchange))
async def cancel_accept(message: Message, state: FSMContext):
    await state.set_state(Name.nothing)
    await message.answer("Ваше действие отменено")
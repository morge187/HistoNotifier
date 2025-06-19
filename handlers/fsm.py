from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext # Новый импорт
from aiogram.fsm.state import State, StatesGroup # Новый импорт

user = Router()

class Test(StatesGroup): # Класс Test
    address = State() # Этап, который должен пройти юзер
    comment = State() # Этап, который должен пройти юзер
    number = State() # Этап, который должен пройти юзер

@user.message(Command('fsm'))
async def start(message: Message, state: FSMContext):
    await state.set_state(Test.address) # Устанавливаем первое состояние (этап)
    await message.answer('Введите адрес для доставки')
    
@user.message(Test.address)
async def comment(message: Message, state: FSMContext):
    await state.update_data(address=message.text) # Ловим первое состояние (этап)
    await state.set_state(Test.comment)
    await message.answer('Введите сообщение для курьера')
    
@user.message(Test.comment)
async def number(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await state.set_state(Test.number)
    await message.answer('Введите свой номер телефона')

@user.message(Test.number)
async def result(message: Message, state: FSMContext):
    await state.update_data(number=message.text)
    data = await state.get_data() # Выводим всю информацию
    await message.answer(f'Ваш адрес: {data["address"]}\nВаш комментарий курьеру: {data["comment"]}\nВаш номер телефона: {data["number"]}')
    await state.clear() # Очищаем все состояния
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram import Router
from aiogram import F
from keyboards import userboard, adminboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database.requests import set_user, set_status, set_name_user, get_user, check_name_exists, set_onboarded

start = Router()

array_exchange = ["отмена", "Отмена", "Cancel", "cancel", "Стоп"]

WELCOME_TEXT = (
    "📖 Как читать обозначения в боте:\n\n"
    "Pz. III A (Pz. III E)\n"
    "Официальное название техники (аналогичное название в игре).\n\n"
    "(Ред.) — техника или сражение сейчас редактируется.\n\n"
    "Если бот перестал отвечать после его удаления/перезапуска, "
    "напиши команду /menu — интерфейс восстановится."
)

ONBOARD_CALLBACK = "onboard_ok"
onboard_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Понятно!", callback_data=ONBOARD_CALLBACK)]
])


async def send_welcome(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=onboard_kb)

class Name(StatesGroup):
    name = State()
    nothing = State()

@start.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await set_user(message.from_user.id)
     # создать юзера
    data = await get_user(message.from_user.id)
    if data.name is not None:
        if not data.onboarded:
            await send_welcome(message)
        return

    await set_status(message.from_user.id, 'base_user') # задать статут обчного юзера
    await message.answer('Тебя приветсивует HistoNotifier бот, напиши свой ник')
    await state.set_state(Name.name)

@start.message(Command("rename"))
@start.message(F.text == 'Поменять имя')
async def chacge_name(message: Message, state: FSMContext):
    await message.answer('Напиши свой ник')
    await state.set_state(Name.name)

async def board_for(tg_id):
    user = await get_user(tg_id)
    return adminboard if user and user.status == 'admin' else userboard


@start.message(Name.name)
async def set_name_to_user(message: Message, state: FSMContext):
    # Стикер, фото и прочее нетекстовое: message.text == None
    if not message.text:
        await message.answer('Ник нужно прислать текстом. Попробуй ещё раз:')
        return

    new_nick = ' '.join(message.text.split())

    # Отмену ловим здесь: пока активно состояние Name.name,
    # до общего обработчика cancel_accept сообщение не доходит
    if new_nick in array_exchange:
        await state.clear()
        await message.answer('Смена ника отменена',
                             reply_markup=await board_for(message.from_user.id))
        return

    if len(new_nick) < 2:
        await message.answer('Ник должен содержать минимум 2 символа. Попробуй ещё раз:')
        return

    # Свой текущий ник занятым не считается, иначе поправить его регистр нельзя
    if await check_name_exists(new_nick, exclude_tg_id=message.from_user.id):
        await message.answer(f'❌ Ник "{new_nick}" уже занят. Выбери другой:')
        return

    await set_name_user(message.from_user.id, new_nick)
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user.onboarded:
        await message.answer(f'✅ Ваш ник "{new_nick}" успешно сохранён', reply_markup=ReplyKeyboardRemove())
        await send_welcome(message)
        return
    await message.answer(f'✅ Ваш ник "{new_nick}" успешно сохранён',
                         reply_markup=await board_for(message.from_user.id))

@start.callback_query(F.data == ONBOARD_CALLBACK)
async def onboard_ok(callback: CallbackQuery):
    await set_onboarded(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Меню открыто 👇", reply_markup=await board_for(callback.from_user.id))
    await callback.answer()

@start.message(F.text.in_(array_exchange))
async def cancel_accept(message: Message, state: FSMContext):
    await state.set_state(Name.nothing)
    await message.answer("Ваше действие отменено")
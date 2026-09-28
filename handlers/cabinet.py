"""Личный кабинет: ник, кадры, награды, тесты, штрафы + оплата и смена ника."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.fines import get_active_fines
from database.requests import get_user, get_user_rewards_with_status
from database.training import get_test_statuses
from handlers.fine_payment import FinePayCb
from handlers.start import Name
from utils import render_cabinet

cabinet_router = Router()

CABINET_BUTTON = "Личный кабинет"
RENAME_CALLBACK = "cab_rename"


@cabinet_router.message(F.text == CABINET_BUTTON)
@cabinet_router.message(Command("cabinet"))
async def show_cabinet(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or not user.name:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    rewards = [(reward.name, ur.issued) for ur, reward in await get_user_rewards_with_status(user.id)]
    tests = [(title, passed) for _, title, passed in await get_test_statuses(user.id)]
    fines = await get_active_fines(user.id)
    text = render_cabinet(user.name, user.points, rewards, tests, [(f.description, f.cost) for f in fines])

    kb = InlineKeyboardBuilder()
    if any(f.cost for f in fines):
        kb.button(text="💳 Оплатить штраф", callback_data=FinePayCb(action="list").pack())
    kb.button(text="✏️ Сменить ник", callback_data=RENAME_CALLBACK)
    kb.adjust(1)
    await message.answer(text, reply_markup=kb.as_markup())


@cabinet_router.callback_query(F.data == RENAME_CALLBACK)
async def cabinet_rename(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Name.name)
    await callback.message.answer("Напиши свой ник")
    await callback.answer()

"""Мелкие общие помощники хендлеров."""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery


async def safe_answer(callback: CallbackQuery, *args, **kwargs) -> None:
    """callback.answer(), не падающий на TelegramBadRequest («query is too old» и т.п.).

    Нужен там, где answer() идёт ПОСЛЕ списания/смены состояния: иначе исключение
    оборвёт хендлер и оплаченное действие (следующий вопрос, сообщение) не случится.
    """
    try:
        await callback.answer(*args, **kwargs)
    except TelegramBadRequest:
        pass

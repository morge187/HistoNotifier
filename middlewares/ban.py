"""Заблокированный пользователь получает короткий ответ, обработчики не вызываются."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.requests import get_user

BAN_TEXT = "🚫 Вы заблокированы"


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        from_user = data.get("event_from_user")
        # Платёж, начатый до блокировки, должен завершиться
        if from_user is None or (isinstance(event, Message) and event.successful_payment):
            return await handler(event, data)

        user = await get_user(from_user.id)
        if user and user.is_banned and user.status != "admin":
            if isinstance(event, CallbackQuery):
                await event.answer(BAN_TEXT, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(BAN_TEXT)
            return None
        return await handler(event, data)

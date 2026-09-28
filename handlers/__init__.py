from aiogram import Router

from .start import start
from .admin_create import admin_create
from .fines import fines_router
from .change_event import admin_edit_router
from .admin_battles import admin_battles
from .admin_training import admin_training
from .usercommands import user
from .fine_payment import fine_payment_router
from .events import events_router
from .reward import reward_router
from .battles import battles_router
from .search import search_router
from .training import training_router
from .cabinet import cabinet_router

# ── Главный роутер (регистрация, ник, отмена) ────────────────────────────────
main_router = Router(name="main")
main_router.include_router(start)

# ── Админский роутер ─────────────────────────────────────────────────────────
admin_router = Router(name="admin")
admin_router.include_router(admin_create)
admin_router.include_router(fines_router)
admin_router.include_router(admin_edit_router)
admin_router.include_router(admin_battles)
admin_router.include_router(admin_training)

# ── Пользовательский роутер ──────────────────────────────────────────────────
user_router = Router(name="user")
user_router.include_router(user)
user_router.include_router(cabinet_router)
user_router.include_router(training_router)
user_router.include_router(events_router)
user_router.include_router(reward_router)
user_router.include_router(battles_router)

# fine_payment_router идёт первым: обработчик successful_payment должен перехватить
# Telegram update до других state-фильтрованных handlers, иначе звёзды могут быть
# потеряны (роутеры ниже имеют FSM-состояния, которые поглощают Message updates).
# search_router идёт вторым: кнопка «🔍 Поиск» должна срабатывать из любого
# состояния, а свои состояния он при необходимости отдаёт дальше (SkipHandler).
handlers = [fine_payment_router, search_router, main_router, admin_router, user_router]

__all__ = ["handlers"]
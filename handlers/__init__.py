from aiogram import Router

from .start import start
from .admin_create import admin_create
from .fines import fines_router
from .change_event import admin_edit_router
from .admin_battles import admin_battles
from .admin_training import admin_training
from .usercommands import user
from .events import events_router
from .reward import reward_router
from .battles import battles_router
from .search import search_router

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
user_router.include_router(events_router)
user_router.include_router(reward_router)
user_router.include_router(battles_router)

# search_router идёт первым: кнопка «🔍 Поиск» должна срабатывать из любого
# состояния, а свои состояния он при необходимости отдаёт дальше (SkipHandler).
handlers = [search_router, main_router, admin_router, user_router]

__all__ = ["handlers"]
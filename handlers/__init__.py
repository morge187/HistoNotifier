from aiogram import Router

from .start import start
from .admin_create import admin_create
from .admin import admin
from .change_event import admin_edit_router
from .admin_battles import admin_battles
from .usercommands import user
from .events import events_router
from .reward import reward_router
from .battles import battles_router

# ── Главный роутер (регистрация, ник, отмена) ────────────────────────────────
main_router = Router(name="main")
main_router.include_router(start)

# ── Админский роутер ─────────────────────────────────────────────────────────
admin_router = Router(name="admin")
admin_router.include_router(admin_create)
admin_router.include_router(admin)
admin_router.include_router(admin_edit_router)
admin_router.include_router(admin_battles)

# ── Пользовательский роутер ──────────────────────────────────────────────────
user_router = Router(name="user")
user_router.include_router(user)
user_router.include_router(events_router)
user_router.include_router(reward_router)
user_router.include_router(battles_router)

handlers = [main_router, admin_router, user_router]

__all__ = ["handlers"]
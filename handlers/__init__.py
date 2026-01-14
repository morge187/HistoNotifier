from .start import start as start
from .admin_create import admin_create
from .usercommands import user
from .admin import admin
from .events import events_router
from .change_event import admin_edit_router
from .reward import reward_router

handlers = [start, admin_create, user,
            admin, events_router, admin_edit_router,
            reward_router]

__all__ = ["handlers"]
from .userkeyboard import *
from .adminkeyboard import adminboard, ADMIN_ROWS

# Тексты всех кнопок главного меню (пользователь + админ). Нажатие любой из них
# в режиме ввода (ник, поиск) закрывает ввод и отдаётся «родному» хендлеру.
MENU_BUTTONS = frozenset(
    button.text for row in user_rows(with_training=True) + ADMIN_ROWS for button in row
)


def is_menu_input(text) -> bool:
    """Команда (/…) или кнопка главного меню — не пользовательский ввод."""
    text = (text or "").strip()
    return text.startswith("/") or text in MENU_BUTTONS

keyboards = [userboard, adminboard]

__all__ = ["keyboards"]
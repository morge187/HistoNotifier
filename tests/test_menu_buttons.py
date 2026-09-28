from keyboards import MENU_BUTTONS, adminboard, is_menu_input, userboard


def test_menu_buttons_cover_both_keyboards():
    texts = {b.text for board in (userboard, adminboard) for row in board.keyboard for b in row}
    assert MENU_BUTTONS == texts
    assert {"Личный кабинет", "Матч-штрафы", "Обучение", "🔍 Поиск", "Тесты ⚙️"} <= MENU_BUTTONS


def test_is_menu_input_buttons_and_commands():
    assert is_menu_input("Личный кабинет")
    assert is_menu_input(" Матч-штрафы ")
    assert is_menu_input("Добавить ивент")
    assert is_menu_input("/menu")
    assert is_menu_input("/cabinet")


def test_is_menu_input_plain_nick():
    assert not is_menu_input("Youra")
    assert not is_menu_input("Личный")
    assert not is_menu_input("")
    assert not is_menu_input(None)

# Глобальное обновление бота — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать 10 пунктов ТЗ из спеки `docs/superpowers/specs/2026-09-27-bot-global-update-design.md`: личный кабинет, обучение, новое меню, штрафы с историей и оплатой (кадры + Telegram Stars), блокировку, GIF-карты, приветствие, правила, годы диапазоном.

**Architecture:** aiogram 3 бот на SQLite (SQLAlchemy async). Новая функциональность — в новых модулях (`database/fines.py`, `database/training.py`, `handlers/fines.py`, `handlers/fine_payment.py`, `handlers/cabinet.py`, `handlers/training.py`, `handlers/admin_training.py`, `middlewares/ban.py`). Схема БД расширяется миграцией при старте (`database/migrate.py`). Задачи сгруппированы в волны: задачи одной волны трогают непересекающиеся файлы/участки и выполняются параллельно в отдельных worktree.

**Tech Stack:** Python 3.14 (venv `venv_new`), aiogram 3.23, SQLAlchemy 2.0.45 async + aiosqlite, pytest.

## Global Constraints

- Python: `C:/my_space/Projects/work_projects/EventBot/venv_new/Scripts/python.exe` (абсолютный путь — в worktree venv нет). Ниже обозначается `$PY`.
- Тесты: `$PY -m pytest -q` из корня рабочей копии.
- Git: добавлять только свои файлы (`git add <path>`). Никогда не `git add -A` / `git add .`. Никогда не коммитить `db.sqlite3`, `__pycache__/`, `venv*/`.
- Коммит-сообщение заканчивается строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Файлы `handlers/__init__.py`, `keyboards/userkeyboard.py`, `keyboards/adminkeyboard.py` меняет только Task 15 (интеграция). `app.py` меняет только Task 10.
- Все тексты интерфейса — на русском, строки из спеки дословно.
- Каждый админский обработчик (message и callback) проверяет `await is_admin(tg_id)` из `database.requests`; при отказе — «Доступно только администратору.» (callback — `show_alert=True`).
- Нажатие на устаревшую кнопку (объект не найден/закрыт) → `callback.answer(<текст>, show_alert=True)`, без исключений.
- Сообщения, где пользовательский текст (ники, описания) подставляется в ответ, отправляются **без** `parse_mode` (или с экранированием `html.escape`, если сообщение уже HTML).
- `message.text` может быть `None` (стикер/фото) — используйте `(message.text or "").strip()`.
- Глобальная отмена уже есть: `handlers/start.py::cancel_accept` ловит «отмена/Отмена/Cancel/cancel/Стоп» в любом состоянии (роутер `main` подключён раньше остальных). Новые FSM-сценарии ничего для отмены не делают.
- Не импортируйте в тестовые модули объекты, чьё имя начинается с `test`/`Test` (pytest попытается их собрать).

## Карта файлов и владельцы

| Волна | Task | Файлы (создать / изменить) |
|---|---|---|
| 1 | 1 | `utils.py`, `tests/__init__.py`, `tests/test_utils.py`, `pytest.ini`, `requirements-dev.txt` |
| 1 | 2 | `database/models.py`, `database/migrate.py`, `tests/conftest.py`, `tests/test_migrate.py` |
| 2 | 3 | `handlers/usercommands.py` (только обработчики годов танка и их подсказки) |
| 2 | 4 | `handlers/admin_battles.py`, `handlers/battles.py`, `database/requests.py` (только `create_battle`) |
| 2 | 5 | `handlers/start.py`, `handlers/usercommands.py` (только правила и `/menu`), `database/requests.py` (только новая `set_onboarded` сразу после `set_name_user`) |
| 2 | 6 | `database/fines.py`, `tests/test_fines_db.py` |
| 2 | 7 | `database/training.py`, `tests/test_training_db.py` |
| 2 | 8 | `database/requests.py` (только новые функции сразу после `get_user_rewards`), `tests/test_rewards_db.py` |
| 3 | 9 | `handlers/fines.py` (создать), `handlers/admin.py` (удалить) |
| 3 | 10 | `middlewares/__init__.py`, `middlewares/ban.py`, `tests/test_ban_middleware.py`, `app.py` |
| 3 | 11 | `handlers/fine_payment.py`, `tests/test_fine_payment.py` |
| 3 | 13 | `handlers/training.py` |
| 3 | 14 | `handlers/admin_training.py` |
| 4 | 12 | `handlers/cabinet.py` (до Task 15) |
| 4 | 15 | `handlers/__init__.py`, `keyboards/userkeyboard.py`, `keyboards/adminkeyboard.py`, `tests/test_imports.py` |

---

## Волна 1

### Task 1: Чистые функции в `utils.py` + инфраструктура pytest

**Files:**
- Modify: `utils.py` (дописать в конец, существующее не трогать)
- Create: `tests/__init__.py` (пустой), `tests/test_utils.py`, `pytest.ini`, `requirements-dev.txt`

**Interfaces — Produces** (все в `utils.py`):
- `STARS_PER_CADR = 5`, `PASS_RATIO = 0.8`, `TEST_COOLDOWN = timedelta(hours=24)`
- `parse_years(text: str | None, min_year: int = 1900, max_year: int | None = None) -> list[int]` — `ValueError` с русским текстом при ошибке
- `fine_stars(cost: float) -> int`
- `parse_amount(text: str | None) -> float` — неотрицательное число, ≤ 2 знаков после запятой, `,` = `.`; `ValueError` с русским текстом
- `parse_options(text: str | None) -> list[str]` — ровно 4 непустые строки; `ValueError`
- `is_quiz_passed(correct: int, total: int) -> bool`
- `cooldown_left(last_fail_at: datetime | None, now: datetime) -> timedelta | None`
- `fmt_duration(delta: timedelta) -> str` — «13 ч 20 мин» / «5 мин»
- `start_decision(passed: bool, last_fail_at: datetime | None, points: float | None, cost: float | None, now: datetime) -> tuple[str, timedelta | None]` — `"passed" | "cooldown" | "no_points" | "ok"`
- `render_cabinet(name: str, points: float | None, rewards: list[tuple[str, bool]], tests: list[tuple[str, bool]], fines: list[tuple[str, float]]) -> str`

- [ ] **Step 1: Инфраструктура**

`pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = .
```
`requirements-dev.txt`:
```
-r requirements.txt
pytest
```

- [ ] **Step 2: Написать падающие тесты** — `tests/test_utils.py`:

```python
from datetime import datetime, timedelta

import pytest

from utils import (
    parse_years, fine_stars, parse_amount, parse_options, is_quiz_passed,
    cooldown_left, fmt_duration, start_decision, render_cabinet,
)

NOW = datetime(2026, 9, 27, 12, 0)


def test_parse_years_range():
    assert parse_years("1941-1945", max_year=2026) == [1941, 1942, 1943, 1944, 1945]


def test_parse_years_mixed_and_dashes():
    assert parse_years("1939, 1941 – 1943, 1942", max_year=2026) == [1939, 1941, 1942, 1943]
    assert parse_years("1941—1942", max_year=2026) == [1941, 1942]


def test_parse_years_single():
    assert parse_years("1942", max_year=2026) == [1942]


@pytest.mark.parametrize("bad", ["", None, "abc", "1945-1941", "1899", "2030", "41-45", "1941-", ","])
def test_parse_years_errors(bad):
    with pytest.raises(ValueError):
        parse_years(bad, max_year=2026)


def test_fine_stars():
    assert fine_stars(1) == 5
    assert fine_stars(1.5) == 8
    assert fine_stars(0.2) == 1       # float noise must not round up to 2
    assert fine_stars(0.01) == 1


def test_parse_amount():
    assert parse_amount("3") == 3
    assert parse_amount("2,5") == 2.5
    assert parse_amount(" 0 ") == 0
    for bad in ["", None, "abc", "-1", "1.234", "nan", "inf"]:
        with pytest.raises(ValueError):
            parse_amount(bad)


def test_parse_options():
    assert parse_options("a\n b \nc\nd") == ["a", "b", "c", "d"]
    assert parse_options("a\n\nb\nc\nd\n") == ["a", "b", "c", "d"]
    for bad in [None, "", "a\nb\nc", "a\nb\nc\nd\ne"]:
        with pytest.raises(ValueError):
            parse_options(bad)


def test_is_quiz_passed():
    assert is_quiz_passed(8, 10)
    assert not is_quiz_passed(7, 10)
    assert is_quiz_passed(20, 25)
    assert not is_quiz_passed(0, 0)


def test_cooldown_left():
    assert cooldown_left(None, NOW) is None
    assert cooldown_left(NOW - timedelta(hours=25), NOW) is None
    assert cooldown_left(NOW - timedelta(hours=24), NOW) is None
    assert cooldown_left(NOW - timedelta(hours=1), NOW) == timedelta(hours=23)


def test_fmt_duration():
    assert fmt_duration(timedelta(hours=13, minutes=20)) == "13 ч 20 мин"
    assert fmt_duration(timedelta(minutes=5)) == "5 мин"
    assert fmt_duration(timedelta(seconds=10)) == "1 мин"


def test_start_decision_order():
    recent = NOW - timedelta(hours=1)
    assert start_decision(True, recent, 0, 10, NOW) == ("passed", None)
    assert start_decision(False, recent, 100, 0, NOW) == ("cooldown", timedelta(hours=23))
    assert start_decision(False, None, 1, 5, NOW) == ("no_points", None)
    assert start_decision(False, None, None, 0, NOW) == ("ok", None)
    assert start_decision(False, None, 5, 5, NOW) == ("ok", None)


def test_render_cabinet_full():
    text = render_cabinet(
        "Youra", 42,
        [("Камуфляж №1", True), ("Камуфляж №2", False)],
        [("Тест А", True), ("Тест Б", False)],
        [("Оскорбление", 3), ("Старый штраф", 0)],
    )
    assert "👤 Ник: Youra" in text
    assert "🎞 Кадры: 42" in text
    assert "Камуфляж №1 — выдан ✅" in text
    assert "Камуфляж №2 — не выдан ❌" in text
    assert "Тест А — пройден 🟢" in text
    assert "Тест Б — не пройден 🔴" in text
    assert "1. Оскорбление — 3 кадров" in text
    assert "2. Старый штраф" in text and "Старый штраф —" not in text


def test_render_cabinet_empty():
    text = render_cabinet("Youra", 0, [], [], [])
    assert "🎁 Награды: нет" in text
    assert "📚 Тесты: нет тестов" in text
    assert "⚠️ Штрафы: нет" in text
```

- [ ] **Step 3: Запустить** `$PY -m pytest tests/test_utils.py -q` — ожидается ImportError.

- [ ] **Step 4: Реализация** — дописать в конец `utils.py` (добавить импорты `import math`, `import re`, `from datetime import datetime, timedelta` в начало файла):

```python
# ── Общие константы ──────────────────────────────────────────────────────────
STARS_PER_CADR = 5
PASS_RATIO = 0.8
TEST_COOLDOWN = timedelta(hours=24)

_YEAR_RANGE = re.compile(r"(\d{4})\s*[-–—]\s*(\d{4})")
_YEAR = re.compile(r"\d{4}")


def parse_years(text, min_year: int = 1900, max_year: int | None = None) -> list[int]:
    """«1939, 1941-1945» → [1939, 1941, 1942, 1943, 1944, 1945]."""
    max_year = max_year or datetime.now().year
    years = set()
    for part in str(text or "").split(","):
        part = part.strip()
        if not part:
            continue
        match = _YEAR_RANGE.fullmatch(part)
        if match:
            start, end = int(match[1]), int(match[2])
            if start > end:
                raise ValueError(f"В диапазоне {part} начало больше конца.")
        elif _YEAR.fullmatch(part):
            start = end = int(part)
        else:
            raise ValueError(f"Не понимаю «{part}». Пример: 1941-1945 или 1939, 1941-1943")
        for year in (start, end):
            if not min_year <= year <= max_year:
                raise ValueError(f"Год {year} вне диапазона {min_year}–{max_year}.")
        years.update(range(start, end + 1))
    if not years:
        raise ValueError("Не указано ни одного года.")
    return sorted(years)


def fine_stars(cost) -> int:
    """Стоимость штрафа в звёздах: 1 кадр = 5 ⭐, округление вверх."""
    return max(1, math.ceil(round(float(cost) * STARS_PER_CADR, 6)))


def parse_amount(text) -> float:
    """Неотрицательное число кадров, не больше 2 знаков после запятой."""
    raw = str(text or "").strip().replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        raise ValueError("Нужно число, например 3 или 2.5")
    if not math.isfinite(value) or value < 0:
        raise ValueError("Нужно неотрицательное число, например 3 или 2.5")
    if "." in raw and len(raw.split(".")[-1]) > 2:
        raise ValueError("Максимум 2 знака после запятой")
    return round(value, 2)


def parse_options(text) -> list[str]:
    """Ровно 4 варианта ответа — по одному на строку."""
    options = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if len(options) != 4:
        raise ValueError(f"Нужно ровно 4 варианта, каждый с новой строки (сейчас {len(options)}).")
    return options


def is_quiz_passed(correct: int, total: int) -> bool:
    return total > 0 and correct / total >= PASS_RATIO


def cooldown_left(last_fail_at, now):
    if last_fail_at is None:
        return None
    left = last_fail_at + TEST_COOLDOWN - now
    return left if left > timedelta(0) else None


def fmt_duration(delta) -> str:
    minutes = max(1, math.ceil(delta.total_seconds() / 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч {minutes} мин" if hours else f"{minutes} мин"


def start_decision(passed, last_fail_at, points, cost, now):
    """Можно ли начать тест: passed → cooldown → no_points → ok."""
    if passed:
        return "passed", None
    left = cooldown_left(last_fail_at, now)
    if left:
        return "cooldown", left
    if (points or 0) < (cost or 0):
        return "no_points", None
    return "ok", None


def render_cabinet(name, points, rewards, tests, fines) -> str:
    """Текст личного кабинета. rewards/tests: (название, флаг); fines: (описание, стоимость)."""
    emoji, _ = cadr_tier(points)
    lines = [f"👤 Ник: {name}", f"🎞 Кадры: {fmt_points(points)} {emoji}".rstrip(), ""]

    if rewards:
        lines.append("🎁 Награды:")
        lines += [f" • {title} — {'выдан ✅' if issued else 'не выдан ❌'}" for title, issued in rewards]
    else:
        lines.append("🎁 Награды: нет")
    lines.append("")

    if tests:
        lines.append("📚 Тесты:")
        lines += [f" • {title} — {'пройден 🟢' if ok else 'не пройден 🔴'}" for title, ok in tests]
    else:
        lines.append("📚 Тесты: нет тестов")
    lines.append("")

    if fines:
        lines.append("⚠️ Штрафы:")
        for i, (description, cost) in enumerate(fines, 1):
            price = f" — {fmt_points(cost)} кадров" if cost else ""
            lines.append(f" {i}. {description}{price}")
    else:
        lines.append("⚠️ Штрафы: нет")
    return "\n".join(lines)
```

- [ ] **Step 5: Запустить** `$PY -m pytest tests/test_utils.py -q` — PASS.

- [ ] **Step 6: Commit**
```bash
git add utils.py tests/__init__.py tests/test_utils.py pytest.ini requirements-dev.txt
git commit -m "feat: add pure helpers for years, fines, quizzes, cabinet"
```

---

### Task 2: Модели и миграция

**Files:**
- Modify: `database/models.py`
- Create: `database/migrate.py`, `tests/conftest.py`, `tests/test_migrate.py`

**Interfaces — Produces:**
- `database.models`: `User.is_banned: bool`, `User.onboarded: bool`, `User.fine` (nullable, legacy), `UserReward.issued: bool`, `Battle.map_media_type: str | None`, новые модели `Fine`, `TrainingTest` (таблица `tests`), `TrainingQuestion` (`test_questions`), `TrainingAttempt` (`test_attempts`).
- `database.migrate.migrate(conn) -> None` — принимает **синхронный** SQLAlchemy `Connection` (вызывается через `run_sync`).
- `tests/conftest.py`: фикстура `db` — временная БД на файле, все таблицы созданы, `async_session` подменён в модулях `database.requests`, `database.fines`, `database.training` (если модуль существует). Возвращает `async_sessionmaker`. Хелпер `run(coro)` = `asyncio.run(coro)`.

- [ ] **Step 1: Модели** — в `database/models.py`:

В `User` заменить строку `fine: Mapped[str] = mapped_column()` и добавить поля:
```python
    fine: Mapped[str] = mapped_column(nullable=True)  # legacy, заменено таблицей fines
    is_banned: Mapped[bool] = mapped_column(default=False)
    onboarded: Mapped[bool] = mapped_column(default=False)
```
В `UserReward` добавить:
```python
    issued: Mapped[bool] = mapped_column(default=False)
```
В `Battle` добавить:
```python
    map_media_type: Mapped[str] = mapped_column(nullable=True)  # photo | animation
```
Перед `async_main` добавить:
```python
class Fine(Base):
    __tablename__ = 'fines'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    description: Mapped[str] = mapped_column()
    cost: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[str] = mapped_column(default='active')  # active | paid | removed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_by = mapped_column(BigInteger, nullable=True)
    paid_with: Mapped[str] = mapped_column(nullable=True)  # cadrs | stars
    stars_amount: Mapped[int] = mapped_column(nullable=True)
    charge_id: Mapped[str] = mapped_column(nullable=True)


class TrainingTest(Base):
    __tablename__ = 'tests'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    cost: Mapped[float] = mapped_column(default=0.0)


class TrainingQuestion(Base):
    __tablename__ = 'test_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey('tests.id', ondelete='CASCADE'))
    position: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column()
    option_1: Mapped[str] = mapped_column()
    option_2: Mapped[str] = mapped_column()
    option_3: Mapped[str] = mapped_column()
    option_4: Mapped[str] = mapped_column()
    correct: Mapped[int] = mapped_column()


class TrainingAttempt(Base):
    __tablename__ = 'test_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    test_id: Mapped[int] = mapped_column(ForeignKey('tests.id', ondelete='CASCADE'))
    correct_count: Mapped[int] = mapped_column()
    total: Mapped[int] = mapped_column()
    passed: Mapped[bool] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```
`async_main` заменить на:
```python
async def async_main():
    from database.migrate import migrate
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(migrate)
```

- [ ] **Step 2: Тестовая фикстура** — `tests/conftest.py`:
```python
import asyncio
import importlib

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database.models import Base

DB_MODULES = ("database.requests", "database.fines", "database.training")


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", poolclass=NullPool)
    session = async_sessionmaker(engine, expire_on_commit=False)

    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    run(init())
    for name in DB_MODULES:
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError:
            continue
        monkeypatch.setattr(module, "async_session", session)
    yield session
    run(engine.dispose())
```
Примечание: `expire_on_commit=False` только в тестах; продовый `async_sessionmaker(engine)` не меняется, поэтому функции БД должны сами загружать нужные атрибуты до выхода из сессии (возвращать объекты, у которых все колонки уже прочитаны — обычный `select` это обеспечивает, но после `commit` атрибуты истекают: перед `commit` читайте нужные значения или используйте `await session.refresh(obj)` после commit).

- [ ] **Step 3: Падающий тест миграции** — `tests/test_migrate.py`:
```python
from sqlalchemy import create_engine, text

from database.migrate import migrate
from database.models import Base

OLD_SCHEMA = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, tg_id BIGINT, status VARCHAR, points FLOAT, fine VARCHAR)",
    "CREATE TABLE userrewards (id INTEGER PRIMARY KEY, user_id INTEGER, reward_id INTEGER, created_at DATETIME)",
    "CREATE TABLE battles (id INTEGER PRIMARY KEY, name VARCHAR, front VARCHAR, date_str VARCHAR, description VARCHAR, map_photo_id VARCHAR, equipment_text VARCHAR)",
    "INSERT INTO users (id, name, tg_id, status, points, fine) VALUES (1, 'A', 11, 'base_user', 5, 'мат в чате'), (2, 'B', 22, 'base_user', 0, NULL), (3, 'C', 33, 'base_user', 0, '  ')",
    "INSERT INTO userrewards (id, user_id, reward_id) VALUES (1, 1, 1)",
    "INSERT INTO battles (id, name, front, date_str, description) VALUES (1, 'X', 'F', 'D', 'desc')",
]


def columns(conn, table):
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}


def prepare(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        for sql in OLD_SCHEMA:
            conn.execute(text(sql))
        Base.metadata.create_all(conn)
        migrate(conn)
    return engine


def test_adds_columns_with_defaults(tmp_path):
    engine = prepare(tmp_path)
    with engine.connect() as conn:
        assert {"is_banned", "onboarded"} <= columns(conn, "users")
        assert "issued" in columns(conn, "userrewards")
        assert "map_media_type" in columns(conn, "battles")
        assert conn.execute(text("SELECT is_banned, onboarded FROM users WHERE id = 1")).one() == (0, 1)
        assert conn.execute(text("SELECT issued FROM userrewards WHERE id = 1")).scalar() == 1
        assert conn.execute(text("SELECT map_media_type FROM battles WHERE id = 1")).scalar() is None


def test_moves_legacy_fines_once(tmp_path):
    engine = prepare(tmp_path)
    with engine.begin() as conn:
        migrate(conn)  # второй прогон ничего не дублирует
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT user_id, description, cost, status FROM fines")).all()
    assert rows == [(1, "мат в чате", 0, "active")]


def test_migrate_is_noop_on_fresh_schema(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        migrate(conn)
        migrate(conn)
        assert conn.execute(text("SELECT COUNT(*) FROM fines")).scalar() == 0
```

- [ ] **Step 4: Запустить** `$PY -m pytest tests/test_migrate.py -q` — FAIL (нет `database.migrate`).

- [ ] **Step 5: Реализация** — `database/migrate.py`:
```python
"""Досоздание колонок в существующих таблицах.

create_all не добавляет колонки в уже существующие таблицы, а db.sqlite3
содержит живые данные — поэтому новые поля добавляем ALTER TABLE.
DEFAULT задаёт значение для уже существующих строк; новые строки
получают значение по умолчанию из модели.
"""
from sqlalchemy import text

COLUMNS = (
    ("users", "is_banned", "BOOLEAN NOT NULL DEFAULT 0"),
    ("users", "onboarded", "BOOLEAN NOT NULL DEFAULT 1"),
    ("userrewards", "issued", "BOOLEAN NOT NULL DEFAULT 1"),
    ("battles", "map_media_type", "VARCHAR"),
)


def _columns(conn, table):
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}


def migrate(conn) -> None:
    for table, column, ddl in COLUMNS:
        existing = _columns(conn, table)
        if existing and column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
    _move_legacy_fines(conn)


def _move_legacy_fines(conn) -> None:
    """Текстовые штрафы из users.fine → таблица fines (один раз на пользователя)."""
    conn.execute(text("""
        INSERT INTO fines (user_id, description, cost, status, created_at)
        SELECT u.id, TRIM(u.fine), 0, 'active', CURRENT_TIMESTAMP
        FROM users u
        WHERE u.fine IS NOT NULL AND TRIM(u.fine) != ''
          AND NOT EXISTS (SELECT 1 FROM fines f WHERE f.user_id = u.id)
    """))
```

- [ ] **Step 6: Запустить** `$PY -m pytest -q` — PASS (включая тесты Task 1, если уже слиты).

- [ ] **Step 7: Проверка на копии живой БД**
```bash
cp db.sqlite3 "$TMP/db_copy.sqlite3"
$PY -c "
from sqlalchemy import create_engine, text
from database.models import Base
from database.migrate import migrate
import os
e = create_engine('sqlite:///' + os.path.join(os.environ['TMP'], 'db_copy.sqlite3'))
with e.begin() as c:
    Base.metadata.create_all(c); migrate(c); migrate(c)
    print(c.execute(text('select count(*) from fines')).scalar(), 'fines')
    print(c.execute(text('select count(*) from users where onboarded = 1')).scalar(), 'onboarded users')
"
```
Ожидается: без ошибок, числа выводятся. Копию не коммитить.

- [ ] **Step 8: Commit**
```bash
git add database/models.py database/migrate.py tests/conftest.py tests/test_migrate.py
git commit -m "feat: add fines/training models and startup migration"
```

---

## Волна 2 (после слияния волны 1)

### Task 3: Годы танка диапазоном

**Files:** Modify `handlers/usercommands.py` — только `process_tank_years`, `process_new_years` и тексты подсказок про годы (строки с «через запятую» в шаге 4/6, в меню редактирования «4. 📅 Годы», в `"Введите новые годы через запятую:"` и `"📅 Введите новые годы создания танка через запятую\nТекущие: ..."`). Правила и `/menu` не трогать (это Task 5).

**Interfaces — Consumes:** `utils.parse_years(text) -> list[int]` (ValueError с готовым русским текстом).

- [ ] **Step 1:** Добавить `parse_years` в импорт из `utils` в начале файла (`from utils import cadr_message, parse_years`).
- [ ] **Step 2:** Тело `process_tank_years` после проверки «отмена» заменить на:
```python
    try:
        valid_years = parse_years(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\nВведите годы ещё раз (например: 1941-1945 или 1939, 1941-1943):")
        return

    await state.update_data(years=valid_years)
    await message.answer(
        f"✅ Годы сохранены: {', '.join(map(str, valid_years))}\n\n"
        "📄 Шаг 5/6: Введите описание танка:",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_description)
```
- [ ] **Step 3:** В `process_new_years` блок `try: ... except ValueError: ...` заменить на:
```python
    try:
        valid_years = parse_years(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\nВведите годы ещё раз (например: 1941-1945 или 1939, 1941-1943):")
        return

    success = await update_tank_years(tank.id, valid_years)
    if success:
        await process_remaining_edits(message, state, choices, 4, f"✅ Годы танка обновлены: {', '.join(map(str, valid_years))}")
    else:
        await message.answer("❌ Не удалось обновить годы танка.")
        await state.clear()
```
- [ ] **Step 4:** Подсказки:
  - шаг 4/6: `"📅 Шаг 4/6: Введите годы создания танка:\n"` + `"<i>Например: 1941-1945 или 1939, 1941-1943</i>"` (строку «Или один год» убрать);
  - меню редактирования: `"4. 📅 Годы\n"`;
  - `"Введите новые годы через запятую:"` → `"Введите новые годы (например: 1941-1945 или 1939, 1941-1943):"`;
  - `f"📅 Введите новые годы создания танка через запятую\nТекущие: {years_str}:"` → `f"📅 Введите новые годы создания танка (например: 1941-1945)\nТекущие: {years_str}:"`.
  Строки «Введите номера через запятую» (выбор полей) НЕ менять.
- [ ] **Step 5:** `$PY -c "import handlers.usercommands"` — без ошибок; `$PY -m pytest -q` — PASS. Удалить импорт `datetime`, только если он больше нигде в файле не используется (проверить grep).
- [ ] **Step 6: Commit** `git add handlers/usercommands.py && git commit -m "feat: accept tank year ranges like 1941-1945"`

---

### Task 4: GIF-карты сражений

**Files:** Modify `handlers/admin_battles.py`, `handlers/battles.py`, `database/requests.py` (только функция `create_battle`).

**Interfaces — Consumes:** `Battle.map_media_type` (Task 2).

- [ ] **Step 1:** `database/requests.py::create_battle` — добавить параметр `map_media_type: str = None` после `map_photo_id` и передать `map_media_type=map_media_type` в `Battle(...)`.
- [ ] **Step 2:** В `handlers/admin_battles.py` рядом с состояниями добавить хелпер:
```python
def _map_media(message: Message) -> tuple[str, str]:
    """file_id и тип карты: GIF приходит как animation, фото — как photo."""
    if message.animation:
        return message.animation.file_id, "animation"
    return message.photo[-1].file_id, "photo"
```
- [ ] **Step 3:** Создание: декоратор `@admin_battles.message(CreateBattle.map_photo, F.content_type == ContentType.PHOTO)` → `@admin_battles.message(CreateBattle.map_photo, F.photo | F.animation)`; тело:
```python
    file_id, media_type = _map_media(message)
    await state.update_data(map_photo_id=file_id, map_media_type=media_type)
```
(дальше без изменений). В вызов `create_battle(...)` добавить `map_media_type=data.get("map_media_type")`.
- [ ] **Step 4:** Редактирование: `@admin_battles.message(EditBattle.new_map, F.content_type == ContentType.PHOTO)` → `@admin_battles.message(EditBattle.new_map, F.photo | F.animation)`; тело:
```python
    file_id, media_type = _map_media(message)
    await _apply_edit(message, state, map_photo_id=file_id, map_media_type=media_type)
```
- [ ] **Step 5:** Тексты: «(фото)» → «(фото или GIF)» во всех подсказках про карту (`"Шаг 4/6: Отправьте карту сражения (фото или GIF):"`, `"4 — Карту (фото или GIF)\n"`, `"Отправьте новую карту (фото или GIF):"`); ошибки: `"Пожалуйста, отправьте фото или GIF (карту сражения):"`, `"Пожалуйста, отправьте фото или GIF (карту):"`.
- [ ] **Step 6:** `handlers/battles.py::show_battle_detail`:
```python
    if battle.map_photo_id:
        if battle.map_media_type == "animation":
            sent = await callback.message.answer_animation(animation=battle.map_photo_id)
        else:
            sent = await callback.message.answer_photo(photo=battle.map_photo_id)
        photo_msg_id = sent.message_id
```
- [ ] **Step 7:** `$PY -c "import handlers.admin_battles, handlers.battles"`; `$PY -m pytest -q` — PASS.
- [ ] **Step 8: Commit** `git add handlers/admin_battles.py handlers/battles.py database/requests.py && git commit -m "feat: allow GIF battle maps"`

---

### Task 5: Приветствие, `/menu`, правила

**Files:** Modify `handlers/start.py`; `handlers/usercommands.py` (только функция правил и `menu`); `database/requests.py` (только новая функция сразу после `set_name_user`).

**Interfaces — Produces:** `database.requests.set_onboarded(tg_id: int) -> None`; `handlers.start.WELCOME_TEXT: str`; callback data `"onboard_ok"`.

- [ ] **Step 1:** `database/requests.py`, сразу после `set_name_user`:
```python
async def set_onboarded(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.onboarded = True
            await session.commit()
```
- [ ] **Step 2:** `handlers/start.py` — импорты: добавить `CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove` из `aiogram.types`, `set_onboarded` из `database.requests`. Константы:
```python
WELCOME_TEXT = (
    "📖 Как читать обозначения в боте:\n\n"
    "Pz. III A (Pz. III E)\n"
    "Официальное название техники (аналогичное название в игре).\n\n"
    "(Ред.) — техника или сражение сейчас редактируется.\n\n"
    "Если бот перестал отвечать после его удаления/перезапуска, "
    "напиши команду /menu — интерфейс восстановится."
)

onboard_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Понятно!", callback_data="onboard_ok")]
])


async def send_welcome(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=onboard_kb)
```
- [ ] **Step 3:** `start_command`: вместо `if data.name != None: return` —
```python
    if data.name is not None:
        if not data.onboarded:
            await send_welcome(message)
        return
```
- [ ] **Step 4:** `set_name_to_user`: после `await set_name_user(...)` и `await state.clear()` —
```python
    user = await get_user(message.from_user.id)
    if not user.onboarded:
        await message.answer(f'✅ Ваш ник "{new_nick}" успешно сохранён', reply_markup=ReplyKeyboardRemove())
        await send_welcome(message)
        return
```
затем существующий ответ с клавиатурой.
- [ ] **Step 5:** Новый обработчик:
```python
@start.callback_query(F.data == "onboard_ok")
async def onboard_ok(callback: CallbackQuery):
    await set_onboarded(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Добро пожаловать! Меню открыто 👇",
                                  reply_markup=await board_for(callback.from_user.id))
    await callback.answer()
```
- [ ] **Step 6:** `handlers/usercommands.py`: строку `"  - Участникам клана [Т-70В]\n"` → `"  - Участникам кланов [Т-70В] и [RENWA]\n"`. Функцию `menu`:
```python
@user.message(Command('menu'))
async def menu(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user.name:
        await message.answer('Сначала зарегистрируйся: /start')
        return
    board = adminboard if user.status == 'admin' else userboard
    await message.answer('Меню', reply_markup=board)
```
- [ ] **Step 7:** `$PY -c "import handlers.start, handlers.usercommands"`; `$PY -m pytest -q` — PASS.
- [ ] **Step 8: Commit** `git add handlers/start.py handlers/usercommands.py database/requests.py && git commit -m "feat: welcome instruction after registration, fix /menu, update rules"`

---

### Task 6: `database/fines.py`

**Files:** Create `database/fines.py`, `tests/test_fines_db.py`.

**Interfaces — Produces** (все async, модуль импортирует `async_session` из `database.models` на уровне модуля — так его подменяет фикстура):
- `add_fine(user_id: int, description: str, cost: float) -> Fine | None` (None — нет пользователя)
- `get_fine(fine_id: int) -> Fine | None`
- `get_active_fines(user_id: int) -> list[Fine]` — порядок по `id`
- `get_users_with_active_fines(event_id: int | None = None) -> list[tuple[User, list[Fine]]]` — только пользователи с `name`, порядок по `User.name`, `Fine.id`; с `event_id` — только участники ивента (через подзапрос `UserEvent`, без дублей)
- `remove_fine(fine_id: int, admin_tg_id: int) -> bool` — только `active` → `removed`
- `pay_fine_with_cadrs(fine_id: int, user_id: int) -> str` — `"ok" | "not_found" | "not_active" | "free" | "no_points"`
- `mark_fine_paid_stars(fine_id: int, stars: int, charge_id: str) -> bool` — True, если штраф был `active`
- `set_banned(user_id: int, banned: bool) -> bool`
- `get_admin_tg_ids() -> list[int]`

- [ ] **Step 1: Тесты** — `tests/test_fines_db.py`:
```python
from database import fines
from database.models import User, UserEvent
from tests.conftest import run


async def _users(session_maker):
    async with session_maker() as s:
        s.add_all([
            User(id=1, name="Bob", tg_id=11, status="base_user", points=10),
            User(id=2, name="Alice", tg_id=22, status="base_user", points=1),
            User(id=3, name="Admin", tg_id=33, status="admin", points=0),
            UserEvent(user_id=1, event_id=7),
            UserEvent(user_id=1, event_id=7),
        ])
        await s.commit()


def test_add_and_list(db):
    run(_users(db))
    f1 = run(fines.add_fine(1, "мат", 3))
    run(fines.add_fine(2, "флуд", 0))
    assert f1.id and f1.status == "active" and f1.cost == 3
    assert run(fines.add_fine(999, "x", 1)) is None
    assert [f.description for f in run(fines.get_active_fines(1))] == ["мат"]
    grouped = run(fines.get_users_with_active_fines())
    assert [(u.name, [f.description for f in fs]) for u, fs in grouped] == [("Alice", ["флуд"]), ("Bob", ["мат"])]
    by_event = run(fines.get_users_with_active_fines(7))
    assert [(u.name, len(fs)) for u, fs in by_event] == [("Bob", 1)]


def test_remove_keeps_history(db):
    run(_users(db))
    f = run(fines.add_fine(1, "мат", 3))
    assert run(fines.remove_fine(f.id, 33)) is True
    assert run(fines.remove_fine(f.id, 33)) is False
    stored = run(fines.get_fine(f.id))
    assert stored.status == "removed" and stored.closed_by == 33 and stored.closed_at
    assert run(fines.get_active_fines(1)) == []


def test_pay_with_cadrs(db):
    run(_users(db))
    f = run(fines.add_fine(1, "мат", 3))
    expensive = run(fines.add_fine(2, "флуд", 5))
    free = run(fines.add_fine(2, "старый", 0))
    assert run(fines.pay_fine_with_cadrs(f.id, 2)) == "not_found"       # чужой штраф
    assert run(fines.pay_fine_with_cadrs(expensive.id, 2)) == "no_points"
    assert run(fines.pay_fine_with_cadrs(free.id, 2)) == "free"
    assert run(fines.pay_fine_with_cadrs(f.id, 1)) == "ok"
    assert run(fines.pay_fine_with_cadrs(f.id, 1)) == "not_active"
    paid = run(fines.get_fine(f.id))
    assert paid.status == "paid" and paid.paid_with == "cadrs"

    async def points():
        async with db() as s:
            return (await s.get(User, 1)).points
    assert run(points()) == 7


def test_pay_with_stars(db):
    run(_users(db))
    f = run(fines.add_fine(1, "мат", 3))
    assert run(fines.mark_fine_paid_stars(f.id, 15, "ch_1")) is True
    assert run(fines.mark_fine_paid_stars(f.id, 15, "ch_2")) is False
    paid = run(fines.get_fine(f.id))
    assert (paid.status, paid.paid_with, paid.stars_amount, paid.charge_id) == ("paid", "stars", 15, "ch_1")


def test_ban_and_admins(db):
    run(_users(db))
    assert run(fines.set_banned(1, True)) is True
    assert run(fines.set_banned(999, True)) is False
    assert run(fines.get_admin_tg_ids()) == [33]
```
- [ ] **Step 2:** `$PY -m pytest tests/test_fines_db.py -q` — FAIL.
- [ ] **Step 3: Реализация** `database/fines.py`:
```python
from datetime import datetime

from sqlalchemy import select, update

from database.models import async_session, Fine, User, UserEvent


async def add_fine(user_id: int, description: str, cost: float):
    async with async_session() as session:
        if not await session.get(User, user_id):
            return None
        fine = Fine(user_id=user_id, description=description, cost=round(float(cost), 2))
        session.add(fine)
        await session.commit()
        await session.refresh(fine)
        return fine


async def get_fine(fine_id: int):
    async with async_session() as session:
        return await session.get(Fine, fine_id)


async def get_active_fines(user_id: int) -> list:
    async with async_session() as session:
        result = await session.scalars(
            select(Fine).where(Fine.user_id == user_id, Fine.status == "active").order_by(Fine.id)
        )
        return list(result)


async def get_users_with_active_fines(event_id: int | None = None) -> list:
    stmt = (
        select(User, Fine)
        .join(Fine, Fine.user_id == User.id)
        .where(Fine.status == "active", User.name.isnot(None))
        .order_by(User.name, Fine.id)
    )
    if event_id is not None:
        participants = select(UserEvent.user_id).where(UserEvent.event_id == event_id)
        stmt = stmt.where(User.id.in_(participants))
    async with async_session() as session:
        rows = (await session.execute(stmt)).all()
    grouped = {}
    for user, fine in rows:
        grouped.setdefault(user.id, (user, []))[1].append(fine)
    return list(grouped.values())


async def remove_fine(fine_id: int, admin_tg_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            update(Fine)
            .where(Fine.id == fine_id, Fine.status == "active")
            .values(status="removed", closed_at=datetime.now(), closed_by=admin_tg_id)
        )
        await session.commit()
        return result.rowcount == 1


async def pay_fine_with_cadrs(fine_id: int, user_id: int) -> str:
    async with async_session() as session:
        fine = await session.get(Fine, fine_id)
        if not fine or fine.user_id != user_id:
            return "not_found"
        if fine.status != "active":
            return "not_active"
        if not fine.cost:
            return "free"
        user = await session.get(User, user_id)
        if (user.points or 0) < fine.cost:
            return "no_points"
        # Условный UPDATE защищает от двойного нажатия: второй не найдёт active
        result = await session.execute(
            update(Fine)
            .where(Fine.id == fine_id, Fine.status == "active")
            .values(status="paid", paid_with="cadrs", closed_at=datetime.now())
        )
        if result.rowcount != 1:
            await session.rollback()
            return "not_active"
        user.points = round((user.points or 0) - fine.cost, 2)
        await session.commit()
        return "ok"


async def mark_fine_paid_stars(fine_id: int, stars: int, charge_id: str) -> bool:
    async with async_session() as session:
        result = await session.execute(
            update(Fine)
            .where(Fine.id == fine_id, Fine.status == "active")
            .values(status="paid", paid_with="stars", stars_amount=stars,
                    charge_id=charge_id, closed_at=datetime.now())
        )
        await session.commit()
        return result.rowcount == 1


async def set_banned(user_id: int, banned: bool) -> bool:
    async with async_session() as session:
        result = await session.execute(update(User).where(User.id == user_id).values(is_banned=banned))
        await session.commit()
        return result.rowcount == 1


async def get_admin_tg_ids() -> list:
    async with async_session() as session:
        return list(await session.scalars(select(User.tg_id).where(User.status == "admin")))
```
Примечание: `session.get(Fine, ...)` после выхода из `async with` возвращает объект с уже загруженными колонками (commit не было) — это безопасно.
- [ ] **Step 4:** `$PY -m pytest -q` — PASS.
- [ ] **Step 5: Commit** `git add database/fines.py tests/test_fines_db.py && git commit -m "feat: fines data layer with history, payments and bans"`

---

### Task 7: `database/training.py`

**Files:** Create `database/training.py`, `tests/test_training_db.py`.

**Interfaces — Produces** (async, кроме `question_to_dict`; `async_session` импортирован на уровне модуля):
- `MAX_QUESTIONS = 25`
- Вопрос как dict: `{"text": str, "options": [str, str, str, str], "correct": int (1..4)}`
- `question_to_dict(q: TrainingQuestion) -> dict`
- `create_test(title: str, cost: float, questions: list[dict]) -> int`
- `get_tests_with_counts() -> list[tuple[TrainingTest, int]]` — по `id`
- `get_test(test_id: int) -> TrainingTest | None`
- `get_questions(test_id: int) -> list[TrainingQuestion]` — по `position, id`
- `update_test(test_id: int, **fields) -> bool` (поля `title`, `cost`)
- `update_question(question_id: int, q: dict) -> bool`
- `add_question(test_id: int, q: dict) -> bool` — False, если теста нет или уже `MAX_QUESTIONS`
- `delete_question(question_id: int) -> bool` — False, если это последний вопрос теста
- `delete_test(test_id: int) -> bool` — удаляет попытки, вопросы, тест (явно, без опоры на FK cascade в SQLite)
- `has_passed(user_id: int, test_id: int) -> bool`
- `last_failed_at(user_id: int, test_id: int) -> datetime | None`
- `get_test_statuses(user_id: int) -> list[tuple[int, str, bool]]` — (test_id, title, пройден) для всех тестов, по `id`
- `charge_points(user_id: int, cost: float) -> bool` — атомарно `points -= cost`, если хватает; `cost == 0` → True без изменений
- `record_attempt(user_id: int, test_id: int, correct: int, total: int, passed: bool) -> bool` — False, если теста уже нет

- [ ] **Step 1: Тесты** — `tests/test_training_db.py`:
```python
from datetime import datetime, timedelta

from database import training
from database.models import User, TrainingAttempt
from tests.conftest import run


def q(n, correct=1):
    return {"text": f"Q{n}", "options": ["a", "b", "c", "d"], "correct": correct}


async def _user(db, points=10):
    async with db() as s:
        s.add(User(id=1, name="Bob", tg_id=11, status="base_user", points=points))
        await s.commit()


def test_create_and_read(db):
    test_id = run(training.create_test("Тест А", 5, [q(1), q(2, 3)]))
    [(test, count)] = run(training.get_tests_with_counts())
    assert (test.id, test.title, test.cost, count) == (test_id, "Тест А", 5, 2)
    questions = run(training.get_questions(test_id))
    assert [x.position for x in questions] == [1, 2]
    assert training.question_to_dict(questions[1]) == q(2, 3)


def test_edit_questions(db):
    test_id = run(training.create_test("T", 0, [q(1)]))
    [only] = run(training.get_questions(test_id))
    assert run(training.delete_question(only.id)) is False      # последний вопрос не удаляется
    assert run(training.update_question(only.id, q(9, 4))) is True
    assert run(training.add_question(test_id, q(2))) is True
    assert [x.text for x in run(training.get_questions(test_id))] == ["Q9", "Q2"]
    assert run(training.update_test(test_id, title="New", cost=2)) is True
    assert run(training.get_test(test_id)).title == "New"


def test_max_questions(db):
    test_id = run(training.create_test("T", 0, [q(i) for i in range(training.MAX_QUESTIONS)]))
    assert run(training.add_question(test_id, q(99))) is False


def test_attempts_and_statuses(db):
    run(_user(db))
    a = run(training.create_test("A", 0, [q(1)]))
    b = run(training.create_test("B", 0, [q(1)]))
    assert run(training.last_failed_at(1, a)) is None
    assert run(training.record_attempt(1, a, 0, 1, False)) is True
    assert run(training.last_failed_at(1, a)) is not None
    assert run(training.has_passed(1, a)) is False
    assert run(training.record_attempt(1, a, 1, 1, True)) is True
    assert run(training.has_passed(1, a)) is True
    assert run(training.get_test_statuses(1)) == [(a, "A", True), (b, "B", False)]
    assert run(training.record_attempt(1, 999, 1, 1, True)) is False


def test_delete_test_cascades(db):
    run(_user(db))
    a = run(training.create_test("A", 0, [q(1), q(2)]))
    run(training.record_attempt(1, a, 1, 2, False))
    assert run(training.delete_test(a)) is True
    assert run(training.get_test(a)) is None
    assert run(training.get_questions(a)) == []
    assert run(training.get_test_statuses(1)) == []


def test_charge_points(db):
    run(_user(db, points=5))
    assert run(training.charge_points(1, 0)) is True
    assert run(training.charge_points(1, 6)) is False
    assert run(training.charge_points(1, 5)) is True
    assert run(training.charge_points(1, 0.01)) is False
```
- [ ] **Step 2:** `$PY -m pytest tests/test_training_db.py -q` — FAIL.
- [ ] **Step 3: Реализация** `database/training.py`:
```python
from sqlalchemy import delete, func, select, update

from database.models import async_session, TrainingAttempt, TrainingQuestion, TrainingTest, User

MAX_QUESTIONS = 25


def _question_columns(q: dict) -> dict:
    o = q["options"]
    return dict(text=q["text"], option_1=o[0], option_2=o[1], option_3=o[2], option_4=o[3],
                correct=int(q["correct"]))


def question_to_dict(q) -> dict:
    return {"text": q.text, "options": [q.option_1, q.option_2, q.option_3, q.option_4],
            "correct": q.correct}


async def create_test(title: str, cost: float, questions: list) -> int:
    async with async_session() as session:
        test = TrainingTest(title=title, cost=round(float(cost), 2))
        session.add(test)
        await session.flush()
        test_id = test.id
        for position, q in enumerate(questions, 1):
            session.add(TrainingQuestion(test_id=test_id, position=position, **_question_columns(q)))
        await session.commit()
        return test_id


async def get_tests_with_counts() -> list:
    stmt = (
        select(TrainingTest, func.count(TrainingQuestion.id))
        .outerjoin(TrainingQuestion, TrainingQuestion.test_id == TrainingTest.id)
        .group_by(TrainingTest.id)
        .order_by(TrainingTest.id)
    )
    async with async_session() as session:
        return [(test, count) for test, count in (await session.execute(stmt)).all()]


async def get_test(test_id: int):
    async with async_session() as session:
        return await session.get(TrainingTest, test_id)


async def get_questions(test_id: int) -> list:
    async with async_session() as session:
        result = await session.scalars(
            select(TrainingQuestion).where(TrainingQuestion.test_id == test_id)
            .order_by(TrainingQuestion.position, TrainingQuestion.id)
        )
        return list(result)


async def update_test(test_id: int, **fields) -> bool:
    async with async_session() as session:
        result = await session.execute(update(TrainingTest).where(TrainingTest.id == test_id).values(**fields))
        await session.commit()
        return result.rowcount == 1


async def update_question(question_id: int, q: dict) -> bool:
    async with async_session() as session:
        result = await session.execute(
            update(TrainingQuestion).where(TrainingQuestion.id == question_id).values(**_question_columns(q))
        )
        await session.commit()
        return result.rowcount == 1


async def add_question(test_id: int, q: dict) -> bool:
    async with async_session() as session:
        if not await session.get(TrainingTest, test_id):
            return False
        count, last = (await session.execute(
            select(func.count(TrainingQuestion.id), func.max(TrainingQuestion.position))
            .where(TrainingQuestion.test_id == test_id)
        )).one()
        if count >= MAX_QUESTIONS:
            return False
        session.add(TrainingQuestion(test_id=test_id, position=(last or 0) + 1, **_question_columns(q)))
        await session.commit()
        return True


async def delete_question(question_id: int) -> bool:
    async with async_session() as session:
        question = await session.get(TrainingQuestion, question_id)
        if not question:
            return False
        count = await session.scalar(
            select(func.count(TrainingQuestion.id)).where(TrainingQuestion.test_id == question.test_id)
        )
        if count <= 1:
            return False
        await session.delete(question)
        await session.commit()
        return True


async def delete_test(test_id: int) -> bool:
    async with async_session() as session:
        await session.execute(delete(TrainingAttempt).where(TrainingAttempt.test_id == test_id))
        await session.execute(delete(TrainingQuestion).where(TrainingQuestion.test_id == test_id))
        result = await session.execute(delete(TrainingTest).where(TrainingTest.id == test_id))
        await session.commit()
        return result.rowcount == 1


async def has_passed(user_id: int, test_id: int) -> bool:
    async with async_session() as session:
        found = await session.scalar(
            select(TrainingAttempt.id).where(TrainingAttempt.user_id == user_id,
                                             TrainingAttempt.test_id == test_id,
                                             TrainingAttempt.passed.is_(True)).limit(1)
        )
        return found is not None


async def last_failed_at(user_id: int, test_id: int):
    async with async_session() as session:
        return await session.scalar(
            select(func.max(TrainingAttempt.created_at)).where(TrainingAttempt.user_id == user_id,
                                                               TrainingAttempt.test_id == test_id,
                                                               TrainingAttempt.passed.is_(False))
        )


async def get_test_statuses(user_id: int) -> list:
    async with async_session() as session:
        passed = set(await session.scalars(
            select(TrainingAttempt.test_id).where(TrainingAttempt.user_id == user_id,
                                                  TrainingAttempt.passed.is_(True))
        ))
        tests = (await session.execute(select(TrainingTest.id, TrainingTest.title).order_by(TrainingTest.id))).all()
    return [(test_id, title, test_id in passed) for test_id, title in tests]


async def charge_points(user_id: int, cost: float) -> bool:
    if not cost:
        return True
    async with async_session() as session:
        result = await session.execute(
            update(User).where(User.id == user_id, User.points >= cost)
            .values(points=func.round(User.points - cost, 2))
        )
        await session.commit()
        return result.rowcount == 1


async def record_attempt(user_id: int, test_id: int, correct: int, total: int, passed: bool) -> bool:
    async with async_session() as session:
        if not await session.get(TrainingTest, test_id):
            return False
        session.add(TrainingAttempt(user_id=user_id, test_id=test_id, correct_count=correct,
                                    total=total, passed=passed))
        await session.commit()
        return True
```
- [ ] **Step 4:** `$PY -m pytest -q` — PASS.
- [ ] **Step 5: Commit** `git add database/training.py tests/test_training_db.py && git commit -m "feat: training tests data layer"`

---

### Task 8: Статус выдачи наград (данные)

**Files:** Modify `database/requests.py` — новые функции **сразу после** `get_user_rewards` (не в конец файла: там правит Task 4). Create `tests/test_rewards_db.py`.

**Interfaces — Produces:**
- `get_user_rewards_with_status(user_id: int) -> list[tuple[UserReward, Reward]]` — новые сверху (`UserReward.created_at desc, UserReward.id desc`)
- `toggle_reward_issued(user_reward_id: int) -> tuple[bool, int, str] | None` — (новое значение `issued`, `tg_id` владельца, название награды)

- [ ] **Step 1: Тесты** — `tests/test_rewards_db.py`:
```python
from database import requests
from database.models import Reward, User, UserReward
from tests.conftest import run


async def _seed(db):
    async with db() as s:
        s.add_all([
            User(id=1, name="Bob", tg_id=11, status="base_user", points=0),
            Reward(id=1, name="Камуфляж №1", gift_link="x", price=5),
            Reward(id=2, name="Камуфляж №2", gift_link="y", price=5),
            UserReward(id=1, user_id=1, reward_id=1),
            UserReward(id=2, user_id=1, reward_id=2),
        ])
        await s.commit()


def test_rewards_with_status_and_toggle(db):
    run(_seed(db))
    rows = run(requests.get_user_rewards_with_status(1))
    assert [(r.name, ur.issued) for ur, r in rows] == [("Камуфляж №2", False), ("Камуфляж №1", False)]
    assert run(requests.toggle_reward_issued(1)) == (True, 11, "Камуфляж №1")
    assert run(requests.toggle_reward_issued(1)) == (False, 11, "Камуфляж №1")
    assert run(requests.toggle_reward_issued(999)) is None


def test_new_purchase_is_not_issued(db):
    run(_seed(db))

    async def buy():
        async with db() as s:
            s.add(Reward(id=3, name="R3", gift_link="z", price=1))
            await s.commit()
        return await requests.assign_reward_to_user(1, 3)

    assert run(buy()) is True
    rows = run(requests.get_user_rewards_with_status(1))
    assert dict((r.name, ur.issued) for ur, r in rows)["R3"] is False
```
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Реализация** (после `get_user_rewards`; `User`, `Reward`, `UserReward` уже импортированы):
```python
async def get_user_rewards_with_status(user_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(UserReward, Reward)
            .join(Reward, Reward.id == UserReward.reward_id)
            .where(UserReward.user_id == user_id)
            .order_by(UserReward.created_at.desc(), UserReward.id.desc())
        )
        return [(user_reward, reward) for user_reward, reward in result.all()]


async def toggle_reward_issued(user_reward_id: int):
    """Переключает «выдан/не выдан». Возвращает (issued, tg_id владельца, название) или None."""
    async with async_session() as session:
        user_reward = await session.get(UserReward, user_reward_id)
        if not user_reward:
            return None
        user_reward.issued = not user_reward.issued
        issued = user_reward.issued
        reward = await session.get(Reward, user_reward.reward_id)
        owner = await session.get(User, user_reward.user_id)
        result = (issued, owner.tg_id, reward.name)
        await session.commit()
        return result
```
- [ ] **Step 4:** `$PY -m pytest -q` — PASS.
- [ ] **Step 5: Commit** `git add database/requests.py tests/test_rewards_db.py && git commit -m "feat: reward issued status queries"`

---

## Волна 3 (после слияния волны 2)

### Task 9: `handlers/fines.py` — матч-штрафы, блокировка, статус наград

**Files:** Create `handlers/fines.py`. Delete `handlers/admin.py` (`git rm`). **Не** трогать `handlers/__init__.py` (Task 15 заменит `from .admin import admin` на `from .fines import fines_router`).

Важно: в `handlers/admin.py` строки 1–202 — мёртвый код (обработчики привязаны к первому `Router()`, который перезаписан на строке 232 и нигде не подключён; живые версии этих сценариев — в `handlers/events.py`). Экспортируемый роутер `admin` содержит только код штрафов (строки 204–648). Мёртвый код не переносить.

**Interfaces:**
- Consumes: `database.fines.{add_fine, get_active_fines, get_users_with_active_fines, remove_fine, set_banned}`; `database.requests.{is_admin, get_user_by_name, get_user_by_id, get_all_users_ordered, get_all_events, get_event_by_index, get_event_participants, set_user_points_value, decrease_user_points, reset_user_points, get_user_rewards_with_status, toggle_reward_issued}`; `utils.{fmt_points, parse_amount}`.
- Produces: `handlers.fines.fines_router: Router`; `FINES_BUTTONS = {"Матч-штрафы", "матч-штрафы"}`.

Поведение (переносится из `handlers/admin.py` 204–648, дальше — изменения):

1. **Вход:** `@fines_router.message(F.text.in_(FINES_BUTTONS))` — как `fine_entry`. Меню «Все игроки / По ивенту / По нику» — без изменений, `CallbackData`-классы `FineMenuCb`, `FineAdminCb`, `BackCb` сохраняют префиксы.
2. **Публичный режим** (не админ) — вместо `User.fine` используется `get_users_with_active_fines(event_id)`:
   - «Все игроки» / «По ивенту»: `"{i}. {user.name} — {'; '.join(f.description for f in fines)}"`; пусто → «Игроки с штрафом отсутствуют».
   - «По нику»: `get_active_fines(user.id)`; пусто → «Нет действующих штрафов»; иначе та же строка.
   - Клик не-админа по админской кнопке: показать ту же строку (или alert «У игрока нет штрафов.»).
3. **Карточка админа** `async def render_admin_user(user) -> str`:
```
Игрок: <name>
Очки: <fmt_points>
Активных штрафов: <n>
🚫 Заблокирован            ← только если user.is_banned
Статус: <status>
tg_id: <tg_id>
```
4. **Клавиатура** `kb_admin_user_actions(user)` (принимает объект пользователя), `adjust(1)`, порядок:
   «Обнулить очки», «Задать очки», «Убавить очки», «Добавить штраф» (`fine_add`), «Штрафы игрока» (`fines_list`), «Награды игрока» (`rewards_list`), «Заблокировать 🚫» (`ban`) или «Разблокировать» (`unban`) — по `user.is_banned`; «Назад» (`BackCb`). Новое действие `card` у `FineAdminCb` — перерисовать карточку (`edit_text`).
5. **Добавить штраф:** `wait_fine_text` → «Введи стоимость штрафа в кадрах (0 — без оплаты):» → `wait_fine_cost` → `parse_amount` (ошибка → текст `ValueError`, остаёмся в состоянии) → `add_fine` → «✅ Штраф добавлен.\n\n» + карточка + клавиатура.
6. **Штрафы игрока:** `CallbackData FineRemoveCb(prefix="fine_rm", fine_id: int, user_id: int)`. Текст: «Активные штрафы {name}:\n1. {описание} — {cost} кадров» (для `cost == 0` без « — …»), пусто → «У {name} нет активных штрафов.». Кнопки «Снять №i» + «◀️ К игроку» (`FineAdminCb(action="card")`). Нажатие «Снять»: `remove_fine(fine_id, callback.from_user.id)`; False → alert «Штраф уже закрыт.»; True → `callback.answer("Штраф снят")` и перерисовка списка (`edit_text`).
7. **Награды игрока:** `CallbackData RewardToggleCb(prefix="rw_tg", user_reward_id: int, user_id: int)`. Текст: «Награды {name}:\n1. {reward.name} — выдан ✅ / не выдан ❌», пусто → «У {name} нет наград.». Кнопки «{'✅' if issued else '❌'} {i}. {name[:30]}» + «◀️ К игроку». Нажатие: `toggle_reward_issued`; None → alert «Награда не найдена.»; если новое значение True — `callback.bot.send_message(tg_id, f"🎁 Награда «{name}» выдана ✅")` в `try/except TelegramAPIError` (ошибка → `callback.answer("Статус изменён, но уведомление не доставлено", show_alert=True)`); перерисовать список.
8. **Блокировка:** `CallbackData BanMsgCb(prefix="ban_msg", user_id: int, ban: bool, with_msg: bool)`.
   - `ban`/`unban`: если цель — админ (`user.status == "admin"`) → alert «Нельзя заблокировать администратора.». Иначе сообщение «Хотите ли вы оставить сообщение пользователю?» с кнопками «Да» (`with_msg=True`) / «Нет» (`with_msg=False`).
   - «Да»: состояние `FineStates.wait_ban_message`, данные `target_user_id`, `ban`; «Введите сообщение».
   - «Нет» / после ввода текста: общий хелпер
```python
async def apply_ban(message: Message, bot, user_id: int, ban: bool, note: str | None):
    user = await get_user_by_id(user_id)
    if not user:
        await message.answer("Игрок не найден.")
        return
    await set_banned(user_id, ban)
    report = f"✅ {user.name} {'заблокирован' if ban else 'разблокирован'}."
    if note is None:
        report += " Без уведомления."
    else:
        header = "🚫 Вы заблокированы." if ban else "✅ Вы разблокированы."
        try:
            await bot.send_message(user.tg_id, f"{header}\n\n{note}")
        except TelegramAPIError:
            report += "\n⚠️ Уведомление не доставлено (пользователь остановил бота)."
    user = await get_user_by_id(user_id)
    await message.answer(report + "\n\n" + await render_admin_user(user),
                         reply_markup=kb_admin_user_actions(user))
```
   (`TelegramAPIError` из `aiogram.exceptions`.)
9. Все message-обработчики состояний админа и все админские callback'и проверяют `is_admin` (как в исходнике).
10. Все ответы с никами/описаниями — без `parse_mode`.

- [ ] **Step 1:** Создать `handlers/fines.py` по описанию выше (перенеся код из `handlers/admin.py` 204–648, импорт `fmt_points`/`parse_amount` из `utils`).
- [ ] **Step 2:** `git rm handlers/admin.py`.
- [ ] **Step 3:** Проверка импорта без `handlers/__init__` (он ещё ссылается на `.admin`): `$PY -c "import importlib.util,sys; spec=importlib.util.spec_from_file_location('fines_mod','handlers/fines.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(m.fines_router)"` — печатает роутер.
- [ ] **Step 4:** `$PY -m pytest -q` — PASS.
- [ ] **Step 5: Commit** `git add handlers/fines.py && git commit -m "feat: fines handlers with removal history, bans and reward status"` (удаление `handlers/admin.py` уже в индексе после `git rm`).

---

### Task 10: Middleware блокировки

**Files:** Create `middlewares/__init__.py`, `middlewares/ban.py`, `tests/test_ban_middleware.py`. Modify `app.py`.

**Interfaces:**
- Consumes: `database.requests.get_user(tg_id)` (поля `is_banned`, `status`).
- Produces: `middlewares.BanMiddleware`, `middlewares.ban.BAN_TEXT = "🚫 Вы заблокированы"`.

- [ ] **Step 1: Тесты** — `tests/test_ban_middleware.py`:
```python
from types import SimpleNamespace
from unittest.mock import AsyncMock

import middlewares.ban as ban
from middlewares.ban import BAN_TEXT, BanMiddleware
from tests.conftest import run


def fake_message(successful_payment=None):
    msg = SimpleNamespace(successful_payment=successful_payment, answer=AsyncMock())
    return msg


def call(monkeypatch, db_user, event, from_user=SimpleNamespace(id=5)):
    monkeypatch.setattr(ban, "get_user", AsyncMock(return_value=db_user))
    handler = AsyncMock(return_value="handled")
    result = run(BanMiddleware()(handler, event, {"event_from_user": from_user}))
    return result, handler


def test_passes_regular_user(monkeypatch):
    result, handler = call(monkeypatch, SimpleNamespace(is_banned=False, status="base_user"), fake_message())
    assert result == "handled" and handler.await_count == 1


def test_blocks_banned_message(monkeypatch):
    event = fake_message()
    result, handler = call(monkeypatch, SimpleNamespace(is_banned=True, status="base_user"), event)
    assert result is None and handler.await_count == 0
    event.answer.assert_awaited_once_with(BAN_TEXT)


def test_admin_never_blocked(monkeypatch):
    result, handler = call(monkeypatch, SimpleNamespace(is_banned=True, status="admin"), fake_message())
    assert result == "handled"


def test_successful_payment_passes(monkeypatch):
    result, handler = call(monkeypatch, SimpleNamespace(is_banned=True, status="base_user"),
                           fake_message(successful_payment=object()))
    assert result == "handled"


def test_unknown_user_passes(monkeypatch):
    result, handler = call(monkeypatch, None, fake_message())
    assert result == "handled"
```
Для `CallbackQuery` проверка через `isinstance` — в middleware используйте `isinstance(event, CallbackQuery)` → `await event.answer(BAN_TEXT, show_alert=True)`; для остальных — `await event.answer(BAN_TEXT)`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Реализация** — `middlewares/ban.py`:
```python
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from database.requests import get_user

BAN_TEXT = "🚫 Вы заблокированы"


class BanMiddleware(BaseMiddleware):
    """Не пускает заблокированных пользователей к обработчикам. Админов не трогает.

    Сообщения об успешной оплате пропускаются всегда, иначе платёж,
    начатый до блокировки, не будет зачтён.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = data.get("event_from_user")
        if from_user is None or getattr(event, "successful_payment", None):
            return await handler(event, data)

        user = await get_user(from_user.id)
        if not user or not user.is_banned or user.status == "admin":
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer(BAN_TEXT, show_alert=True)
        else:
            await event.answer(BAN_TEXT)
        return None
```
`middlewares/__init__.py`:
```python
from .ban import BanMiddleware

__all__ = ["BanMiddleware"]
```
- [ ] **Step 4:** `app.py` — импорт `from middlewares import BanMiddleware`; в `main()` перед `for router in handlers:`:
```python
    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())
```
- [ ] **Step 5:** `$PY -m pytest -q` — PASS.
- [ ] **Step 6: Commit** `git add middlewares/__init__.py middlewares/ban.py tests/test_ban_middleware.py app.py && git commit -m "feat: block banned users via middleware"`

---

### Task 11: `handlers/fine_payment.py` — оплата штрафов

**Files:** Create `handlers/fine_payment.py`, `tests/test_fine_payment.py`.

**Interfaces:**
- Consumes: `database.fines.{get_fine, get_active_fines, pay_fine_with_cadrs, mark_fine_paid_stars, get_admin_tg_ids}`; `database.requests.get_user`; `utils.{fine_stars, fmt_points}`.
- Produces: `fine_payment_router: Router`; `class FinePayCb(CallbackData, prefix="fpay")` с полями `action: str` (`list | choose | cadrs | stars`), `fine_id: int`; `fine_payload(fine_id: int) -> str` (`"fine:<id>"`); `parse_fine_payload(payload: str) -> int | None`.

- [ ] **Step 1: Тесты** — `tests/test_fine_payment.py`:
```python
from handlers.fine_payment import FinePayCb, fine_payload, parse_fine_payload


def test_payload_roundtrip():
    assert parse_fine_payload(fine_payload(42)) == 42


def test_bad_payloads():
    for bad in ["", "fine:", "fine:x", "reward:1", None]:
        assert parse_fine_payload(bad) is None


def test_callback_pack_short():
    assert len(FinePayCb(action="stars", fine_id=10**9).pack()) <= 64
```
Примечание: импорт `handlers.fine_payment` выполняет `handlers/__init__.py`. До Task 15 он импортирует `.admin`, который удалён Task 9 в параллельной ветке — в вашем worktree `handlers/admin.py` ещё существует, так что импорт работает.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3: Реализация.** Поведение:
  - `FinePayCb(action="list", fine_id=0)`: пользователь `get_user(callback.from_user.id)`; активные штрафы с `cost > 0`; пусто → alert «Нет штрафов для оплаты»; иначе новое сообщение «Выберите штраф для оплаты:» + кнопки `f"{i}. {description[:40]} — {fmt_points(cost)} кадров"` → `choose`.
  - `choose`: `get_fine`; нет / не `active` / чужой → alert «Штраф уже закрыт.»; иначе `edit_text` «Штраф: {description}\nСтоимость: {fmt_points(cost)} кадров или {fine_stars(cost)} ⭐» + кнопки «🎞 Кадрами — {fmt_points(cost)}» (`cadrs`), «⭐ Звёздами — {fine_stars(cost)}» (`stars`).
  - `cadrs`: `pay_fine_with_cadrs(fine_id, user.id)`; `"ok"` → `edit_text("✅ Штраф оплачен кадрами.")`; `"no_points"` → alert «Недостаточно кадров»; `"not_active"`/`"not_found"` → alert «Штраф уже закрыт.»; `"free"` → alert «Этот штраф нельзя оплатить — его снимает администратор.».
  - `stars`: проверки как в `choose`, затем
```python
    stars = fine_stars(fine.cost)
    await callback.message.answer_invoice(
        title="Оплата матч-штрафа",
        description=fine.description[:255],
        payload=fine_payload(fine.id),
        currency="XTR",
        prices=[LabeledPrice(label="Матч-штраф", amount=stars)],
    )
    await callback.answer()
```
  - `@fine_payment_router.pre_checkout_query()`:
```python
async def fine_pre_checkout(query: PreCheckoutQuery):
    fine_id = parse_fine_payload(query.invoice_payload)
    fine = await get_fine(fine_id) if fine_id else None
    user = await get_user(query.from_user.id)
    if (not fine or not user or fine.user_id != user.id or fine.status != "active"
            or query.currency != "XTR" or query.total_amount != fine_stars(fine.cost)):
        await query.answer(ok=False, error_message="Штраф уже закрыт или изменился. Откройте личный кабинет заново.")
        return
    await query.answer(ok=True)
```
  - `@fine_payment_router.message(F.successful_payment)`:
```python
async def fine_paid(message: Message):
    payment = message.successful_payment
    fine_id = parse_fine_payload(payment.invoice_payload)
    if fine_id is None:
        return
    charge_id = payment.telegram_payment_charge_id
    if await mark_fine_paid_stars(fine_id, payment.total_amount, charge_id):
        await message.answer("✅ Штраф оплачен звёздами. Спасибо!")
        return
    await message.answer("Оплата получена, но штраф уже был закрыт. Администратор вернёт звёзды.")
    note = (f"⚠️ Оплата за уже закрытый штраф #{fine_id}\n"
            f"Пользователь: {message.from_user.id}\nЗвёзд: {payment.total_amount}\ncharge_id: {charge_id}")
    for tg_id in await get_admin_tg_ids():
        try:
            await message.bot.send_message(tg_id, note)
        except TelegramAPIError:
            pass
```
  - `fine_payload` / `parse_fine_payload`:
```python
def fine_payload(fine_id: int) -> str:
    return f"fine:{fine_id}"


def parse_fine_payload(payload) -> int | None:
    prefix, _, raw = str(payload or "").partition(":")
    if prefix != "fine" or not raw.isdigit():
        return None
    return int(raw)
```
- [ ] **Step 4:** `$PY -m pytest -q` — PASS.
- [ ] **Step 5: Commit** `git add handlers/fine_payment.py tests/test_fine_payment.py && git commit -m "feat: pay fines with cadrs or Telegram Stars"`

---

### Task 13: `handlers/training.py` — «Обучение» для пользователя

**Files:** Create `handlers/training.py`.

**Interfaces:**
- Consumes: `database.training.{get_tests_with_counts, get_test, get_questions, question_to_dict, has_passed, last_failed_at, get_test_statuses, charge_points, record_attempt}`; `database.requests.get_user`; `utils.{fmt_points, start_decision, fmt_duration, is_quiz_passed}`.
- Produces: `training_router: Router`; `TRAINING_BUTTON = "Обучение"`.

Поведение:
- `TrainCb(CallbackData, prefix="train")`: `action: str` (`open | start`), `test_id: int`. `TrainAnswerCb(CallbackData, prefix="train_ans")`: `index: int`, `option: int`. `TrainStates.in_test`.
- `cost_text(cost) -> str`: `"бесплатно"` при 0, иначе `f"{fmt_points(cost)} кадров"`.
- `F.text == TRAINING_BUTTON` / `Command("training")`: нет регистрации → «Сначала зарегистрируйтесь с помощью /start». Нет тестов → «📚 Тестов пока нет.». Иначе текст
```
📚 Обучение

1. <title> — <count> вопросов — <cost_text> 🟢|🔴
```
  (статус из `get_test_statuses`) + кнопки `f"{i}. {title}"` → `open`, `adjust(1)`.
- `open`: тест не найден → alert «Тест не найден.». Иначе новое сообщение `f"📘 {title}\n\nВопросов: {n}\nСтоимость: {cost_text}\nДля прохождения нужно 80% верных ответов."` + кнопка «▶️ Начать» → `start`.
- `start`: тест/вопросы не найдены → alert «Тест не найден.»; `start_decision(await has_passed(...), await last_failed_at(...), user.points, test.cost, datetime.now())`:
  - `passed` → alert «✅ Тест уже пройден»; `cooldown` → alert `f"Попробуй через {fmt_duration(left)}"`; `no_points` → alert «Недостаточно кадров».
  - `ok` → `if not await charge_points(user.id, test.cost)`: alert «Недостаточно кадров»; иначе:
```python
    await state.set_state(TrainStates.in_test)
    await state.set_data({"tt_id": test.id, "tt_title": test.title,
                          "tt_q": [question_to_dict(q) for q in questions], "tt_i": 0, "tt_ok": 0})
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await send_question(callback.message, await state.get_data())
```
- `send_question(message, data)`: текст `f"❓ Вопрос {i+1}/{total}\n\n{text}\n\n1. ...\n2. ...\n3. ...\n4. ..."`, кнопки «1»…«4» (`TrainAnswerCb(index=i, option=n)`), `adjust(4)`. Без `parse_mode`.
- `TrainAnswerCb.filter()`:
  - состояние не `TrainStates.in_test` → alert «Тест прерван. Начни заново через «Обучение».» и снять кнопки (`edit_reply_markup(None)` в `try/except TelegramAPIError`).
  - `callback_data.index != data["tt_i"]` → `callback.answer()` и выход (устаревшая кнопка/двойной клик).
  - иначе: `ok += option == q["correct"]`, `i += 1`, `update_data`, `edit_text(message.text + f"\n\nТвой ответ: {option}")` (без кнопок), `callback.answer()`; если `i < total` — `send_question`; иначе финиш:
```python
    await state.clear()
    passed = is_quiz_passed(ok, total)
    user = await get_user(callback.from_user.id)
    await record_attempt(user.id, data["tt_id"], ok, total, passed)
    if passed:
        text = f"✅ Тест «{data['tt_title']}» пройден! {ok} из {total} верно."
    else:
        text = f"{total - ok} ошибок из {total}. Попробуй ещё раз через 24 ч."
    await callback.message.answer(text)
```
- [ ] **Step 1:** Реализация по описанию.
- [ ] **Step 2:** `$PY -c "import handlers.training"`; `$PY -m pytest -q` — PASS.
- [ ] **Step 3: Commit** `git add handlers/training.py && git commit -m "feat: training section for users"`

---

### Task 14: `handlers/admin_training.py` — конструктор тестов

**Files:** Create `handlers/admin_training.py`.

**Interfaces:**
- Consumes: `database.training.{MAX_QUESTIONS, create_test, get_tests_with_counts, get_test, get_questions, update_test, update_question, add_question, delete_question, delete_test}`; `database.requests.is_admin`; `utils.{parse_amount, parse_options, fmt_points}`.
- Produces: `admin_training_router: Router`; `TESTS_ADMIN_BUTTON = "Тесты ⚙️"`.

Поведение (все обработчики проверяют `is_admin`):
- CallbackData: `ATestCb(prefix="atest")`: `action: str`, `test_id: int = 0`; действия: `create`, `edit_list`, `delete_list`, `edit`, `title`, `cost`, `questions`, `add_q`, `del_q_list`, `delete`, `delete_yes`, `menu_back`. `AQuestionCb(prefix="aq")`: `action: str` (`edit | delete`), `question_id: int`, `test_id: int`. `ACorrectCb(prefix="acorr")`: `option: int`.
- Состояния `ATestStates`: `title`, `cost`, `count`, `q_text`, `q_options`, `q_correct`, `new_title`, `new_cost`.
- Вход `F.text == TESTS_ADMIN_BUTTON`: «⚙️ Тесты» + кнопки «Создать», «Изменить», «Удалить» (`adjust(3)`).
- **Создать:** «Введите название теста:» → `title` (≥ 2 символов) → «Стоимость в кадрах (0 — бесплатно):» → `cost` (`parse_amount`) → `f"Сколько вопросов? (1–{MAX_QUESTIONS})"` → `count` (целое 1..25) → `state.update_data(mode="create", q_total=n, questions=[])` → цикл вопроса.
- **Цикл вопроса** (общий для create / edit_q / add_q):
  - `ask_question_text(message, data)`: для `create` — `f"Вопрос {len(questions)+1}/{q_total}: введите текст вопроса"`, иначе «Введите текст вопроса:» → `q_text`.
  - `q_text` (непустой) → `cur_text` → «Отправьте 4 варианта ответа одним сообщением, каждый с новой строки:» → `q_options`.
  - `q_options` → `parse_options` (ошибка → текст, остаёмся) → `cur_options` → «Какой вариант правильный?» + кнопки `ACorrectCb(1..4)`, `adjust(4)` → `q_correct`.
  - `ACorrectCb` в состоянии `q_correct` (в другом состоянии → alert «Кнопка устарела.»): `q = {"text": cur_text, "options": cur_options, "correct": option}`, убрать кнопки, затем по `mode`:
    - `create`: добавить в `questions`; если ещё не все — следующий вопрос; иначе `test_id = await create_test(title, cost, questions)`, `state.clear()`, «✅ Тест «{title}» создан ({n} вопросов).».
    - `edit_q`: `update_question(question_id, q)` → «✅ Вопрос обновлён.» (или «❌ Вопрос не найден.»), `state.clear()`, меню теста.
    - `add_q`: `add_question(test_id, q)` → «✅ Вопрос добавлен.» (False → «❌ Не удалось: достигнут лимит или тест удалён.»), `state.clear()`, меню теста.
- **Изменить:** `edit_list` → список тестов кнопками → `edit` → `send_test_menu(message, test_id)`:
  текст `f"📘 {title}\nСтоимость: {'бесплатно' if not cost else fmt_points(cost) + ' кадров'}\nВопросов: {n}"`, кнопки: «✏️ Название» (`title`), «💰 Стоимость» (`cost`), «📝 Вопросы» (`questions`), «➕ Добавить вопрос» (`add_q`, только если `n < MAX_QUESTIONS`), «➖ Удалить вопрос» (`del_q_list`, только если `n > 1`); `adjust(1)`. Тест не найден → «Тест не найден.».
  - `title` → `new_title` → `update_test(test_id, title=...)` → меню. `cost` → `new_cost` → `parse_amount` → `update_test(test_id, cost=...)` → меню.
  - `questions` → кнопки `f"{i}. {text[:40]}"` → `AQuestionCb(action="edit")` → `state.update_data(mode="edit_q", question_id=..., test_id=...)` → `ask_question_text`.
  - `add_q` → `state.update_data(mode="add_q", test_id=...)` → `ask_question_text`.
  - `del_q_list` → кнопки вопросов `AQuestionCb(action="delete")` → `delete_question` (False → alert «Нельзя удалить последний вопрос.») → меню.
- **Удалить:** `delete_list` → список тестов → `delete` → «Удалить тест «{title}»? Попытки пользователей тоже удалятся.» + «Да, удалить» (`delete_yes`) / «Отмена» (`menu_back` → просто `edit_text("Отменено.")`) → `delete_test` → «🗑 Тест удалён.».
- Пустой список тестов в `edit_list`/`delete_list` → alert «Тестов пока нет.».

- [ ] **Step 1:** Реализация по описанию.
- [ ] **Step 2:** `$PY -c "import handlers.admin_training"`; `$PY -m pytest -q` — PASS.
- [ ] **Step 3: Commit** `git add handlers/admin_training.py && git commit -m "feat: admin test constructor"`

---

## Волна 4

### Task 12: `handlers/cabinet.py` — личный кабинет

**Files:** Create `handlers/cabinet.py`.

**Interfaces:**
- Consumes: `utils.render_cabinet`; `database.requests.{get_user, get_user_rewards_with_status}`; `database.training.get_test_statuses` (→ `(id, title, passed)`); `database.fines.get_active_fines`; `handlers.fine_payment.FinePayCb` (`action="list", fine_id=0`); `handlers.start.Name` (состояние `Name.name`).
- Produces: `cabinet_router: Router`; `CABINET_BUTTON = "Личный кабинет"`.

- [ ] **Step 1:** Реализация:
```python
from aiogram import F, Router
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


@cabinet_router.message(F.text == CABINET_BUTTON)
@cabinet_router.message(Command("cabinet"))
async def show_cabinet(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user.name:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    rewards = [(reward.name, user_reward.issued)
               for user_reward, reward in await get_user_rewards_with_status(user.id)]
    tests = [(title, passed) for _, title, passed in await get_test_statuses(user.id)]
    fines = await get_active_fines(user.id)

    kb = InlineKeyboardBuilder()
    if any(fine.cost for fine in fines):
        kb.button(text="💳 Оплатить штраф", callback_data=FinePayCb(action="list", fine_id=0).pack())
    kb.button(text="✏️ Сменить ник", callback_data="cab_rename")
    kb.adjust(1)

    await message.answer(
        render_cabinet(user.name, user.points, rewards, tests,
                       [(fine.description, fine.cost) for fine in fines]),
        reply_markup=kb.as_markup(),
    )


@cabinet_router.callback_query(F.data == "cab_rename")
async def cabinet_rename(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Name.name)
    await callback.message.answer("Напиши свой ник")
    await callback.answer()
```
- [ ] **Step 2:** `$PY -c "import handlers.cabinet"` — без ошибок (Task 12 выполняется в волне 4, когда `handlers/fine_payment.py` уже слит; `handlers/__init__.py` на этот момент может ещё ссылаться на удалённый `.admin` — тогда проверяйте импорт через `importlib.util.spec_from_file_location`, как в Task 9 Step 3). `$PY -m pytest -q` — PASS.
- [ ] **Step 3: Commit** `git add handlers/cabinet.py && git commit -m "feat: personal cabinet"`

---

### Task 15: Интеграция — роутеры и клавиатуры

**Files:** Modify `handlers/__init__.py`, `keyboards/userkeyboard.py`, `keyboards/adminkeyboard.py`. Create `tests/test_imports.py`.

- [ ] **Step 1:** `handlers/__init__.py`:
  - `from .admin import admin` → `from .fines import fines_router`; добавить импорты `fine_payment_router`, `cabinet_router`, `training_router`, `admin_training_router`.
  - `admin_router`: `admin_create`, `fines_router`, `admin_edit_router`, `admin_battles`, `admin_training_router`.
  - `user_router`: `cabinet_router`, `fine_payment_router`, `training_router`, затем существующие `user`, `events_router`, `reward_router`, `battles_router`.
- [ ] **Step 2:** `keyboards/userkeyboard.py`:
```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def user_rows():
    return [
        [KeyboardButton(text='Личный кабинет'), KeyboardButton(text='Правила'), KeyboardButton(text='🔍 Поиск')],
        [KeyboardButton(text='Матч-штрафы'), KeyboardButton(text='Обучение'), KeyboardButton(text='Награды')],
        [KeyboardButton(text='Список танков'), KeyboardButton(text='Список сражений'), KeyboardButton(text='Список ивентов')],
    ]


userboard = ReplyKeyboardMarkup(keyboard=user_rows(), resize_keyboard=True)
```
- [ ] **Step 3:** `keyboards/adminkeyboard.py`:
```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from .userkeyboard import user_rows

adminboard = ReplyKeyboardMarkup(keyboard=user_rows() + [
    [KeyboardButton(text='Добавить ивент'), KeyboardButton(text='Редактировать ивент'), KeyboardButton(text='Удалить ивент')],
    [KeyboardButton(text='Добавить награду'), KeyboardButton(text='Изменить награду'), KeyboardButton(text='Удалить награду')],
    [KeyboardButton(text='Добавить танк'), KeyboardButton(text='Изменить танк'), KeyboardButton(text='Удалить танк')],
    [KeyboardButton(text='Добавить сражение'), KeyboardButton(text='Изменить сражение'), KeyboardButton(text='Удалить сражение')],
    [KeyboardButton(text='Тесты ⚙️')],
], resize_keyboard=True)
```
- [ ] **Step 4:** `tests/test_imports.py` — каждая кнопка клавиатур имеет обработчик (текст упоминается в handlers):
```python
import pathlib

import handlers  # noqa: F401  — импорт всех роутеров не падает
from keyboards import adminboard, userboard

SOURCES = "\n".join(p.read_text(encoding="utf-8") for p in pathlib.Path("handlers").glob("*.py"))


def test_every_button_has_handler():
    for board in (userboard, adminboard):
        for row in board.keyboard:
            for button in row:
                assert button.text in SOURCES, button.text
```
- [ ] **Step 5:** `$PY -m pytest -q` — PASS; `$PY -c "import app"` — без ошибок.
- [ ] **Step 6: Commit** `git add handlers/__init__.py keyboards/userkeyboard.py keyboards/adminkeyboard.py tests/test_imports.py && git commit -m "feat: wire new routers and 3x3 main menu"`

---

## Ручной чек-лист (после Task 15, в Telegram)

1. Новый аккаунт: `/start` → ник → инструкция без меню → «Понятно!» → меню 3×3.
2. Старый пользователь: приветствие не приходит; `/menu` показывает новое меню.
3. «Правила» — строка «[Т-70В] и [RENWA]».
4. Добавить танк с годами `1941-1945` → в карточке 1941…1945; изменить годы на `1939, 1941-1942`.
5. Добавить сражение с GIF-картой → в «Список сражений» карта анимирована, «Назад» удаляет её.
6. Админ: «Матч-штрафы» → по нику → «Добавить штраф» (описание, 2 кадра) → «Штрафы игрока» → «Снять» → в БД статус `removed`.
7. Пользователь: «Личный кабинет» → штраф → «Оплатить штраф» → кадрами (при нехватке — alert) / звёздами (инвойс на 10 ⭐).
8. Админ: «Награды игрока» → переключить ✅ → пользователю пришло уведомление, в кабинете «выдан ✅».
9. Админ: «Заблокировать 🚫» → «Да» → текст → пользователь получил сообщение, любая кнопка → «🚫 Вы заблокированы»; «Разблокировать» → «Нет» → доступ вернулся.
10. Админ: «Тесты ⚙️» → создать тест на 5 вопросов, стоимость 1 → пользователь: «Обучение» → пройти с 3/5 → «2 ошибок из 5. Попробуй ещё раз через 24 ч.», повторный старт → «Попробуй через 23 ч 59 мин»; кадры списаны.

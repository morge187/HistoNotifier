# Глобальное обновление бота — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать 10 пунктов ТЗ: личный кабинет, обучение с тестами, новое меню, штрафы с историей и оплатой (кадры / Telegram Stars), GIF-карты, приветствие, блокировку, правка правил, годы танков диапазоном.

**Architecture:** aiogram 3 + SQLAlchemy async (SQLite). Новая функциональность — в отдельных модулях (`handlers/fines.py`, `handlers/fine_payment.py`, `handlers/cabinet.py`, `handlers/training.py`, `handlers/admin_training.py`, `database/fines.py`, `database/training.py`, `database/migrate.py`, `middlewares/ban.py`). Чистая логика (парсинг, расчёты, рендер текста) — в `utils.py` и покрывается pytest. Схема БД дополняется идемпотентной миграцией при старте.

**Tech Stack:** Python 3.14 (`venv_new`), aiogram 3.23, SQLAlchemy 2.0.45, aiosqlite, pytest.

**Spec:** `docs/superpowers/specs/2026-09-27-bot-global-update-design.md`

## Global Constraints

- Интерпретатор: `venv_new/Scripts/python.exe` (Windows). Тесты: `venv_new/Scripts/python.exe -m pytest tests -v`.
- **Коммитить только свои файлы** через `git add <путь>`. Никогда не добавлять `db.sqlite3`, `__pycache__/`, `venv/`, `venv_new/` (в рабочей копии уже есть посторонние изменения — не трогать их).
- Коммит-сообщения заканчиваются строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Весь текст для пользователя — на русском.
- Каждый админский обработчик (сообщение и callback) заново проверяет `is_admin(tg_id)`.
- Нетекстовые сообщения: использовать `(message.text or "").strip()`, никогда `message.text.strip()` в новом коде.
- Курс оплаты: 1 кадр = 5 ⭐, звёзды = `ceil(cost * 5)`. Валюта Stars — `"XTR"`.
- Порог теста — 80%, кулдаун после провала — 24 ч, максимум вопросов — 25, вариантов — ровно 4.
- Имена, начинающиеся на `test`/`Test`, не использовать для прикладных функций и классов (pytest пытается их собирать): классы моделей — `TrainingTest`, `TrainingQuestion`, `TrainingAttempt`; функция проверки результата — `is_quiz_passed`.
- Глобальная отмена: слово «отмена» в любом состоянии ловит `cancel_accept` в `handlers/start.py` (роутер `main_router` подключён раньше админского и пользовательского). Новые роутеры подключать **после** `main_router`.

## Карта файлов

| Файл | Задача | Ответственность |
|---|---|---|
| `pytest.ini`, `requirements-dev.txt`, `tests/conftest.py` | 1, 6 | Тестовая инфраструктура, фикстура временной БД |
| `utils.py` | 1, 11 | Чистые функции: годы, суммы, варианты ответа, звёзды, тесты, рендер кабинета |
| `database/models.py` | 2 | Новые колонки и таблицы |
| `database/migrate.py` | 2 | Идемпотентная миграция SQLite |
| `handlers/usercommands.py` | 3, 5 | Годы танков, правила, `/menu` |
| `handlers/admin_battles.py`, `handlers/battles.py` | 4 | GIF-карты |
| `handlers/start.py` | 5 | Приветствие |
| `database/fines.py` | 6 | Запросы к `fines` |
| `database/requests.py` | 4, 5, 8, 10 | `create_battle(map_media_type)`, `set_onboarded`, `set_banned`, `get_admin_tg_ids`, награды со статусом |
| `handlers/fines.py` (вместо `handlers/admin.py`) | 7, 8, 10 | Матч-штрафы, блокировка, статус наград |
| `middlewares/ban.py` | 8 | Блокировка |
| `handlers/fine_payment.py` | 9 | Оплата штрафов |
| `handlers/cabinet.py`, `keyboards/*` | 11, 14 | Кабинет, меню |
| `database/training.py` | 11, 12 | Тесты |
| `handlers/training.py` | 13 | Прохождение тестов |
| `handlers/admin_training.py` | 14 | Конструктор тестов |

---

## Этап 1 — основа, приветствие, GIF, годы, правила

### Task 1: Тестовая инфраструктура и чистые функции в `utils.py`

**Files:**
- Create: `pytest.ini`, `requirements-dev.txt`, `tests/__init__.py` (пустой), `tests/test_utils.py`
- Modify: `utils.py` (дописать в конец; добавить импорты в начало)

**Interfaces:**
- Produces (в `utils.py`):
  - `STARS_PER_CADR = 5`, `PASS_RATIO = 0.8`, `TEST_COOLDOWN = timedelta(hours=24)`
  - `parse_years(text, min_year=1900, max_year=None) -> list[int]` — `ValueError` с текстом для пользователя
  - `parse_amount(text) -> float` — неотрицательное число, ≤ 2 знаков после запятой; `ValueError`
  - `parse_options(text) -> list[str]` — ровно 4 непустые строки; `ValueError`
  - `fine_stars(cost) -> int`
  - `fine_payload(fine_id: int, user_id: int) -> str`, `parse_fine_payload(payload) -> tuple[int, int] | None`
  - `is_quiz_passed(correct: int, total: int) -> bool`
  - `cooldown_left(last_fail_at: datetime | None, now: datetime) -> timedelta | None`
  - `fmt_duration(delta: timedelta) -> str`
  - `start_decision(passed: bool, last_fail_at, points, cost, now) -> tuple[str, timedelta | None]` — `"passed" | "cooldown" | "no_points" | "ok"`
  - `fmt_cost(cost) -> str` — `"бесплатно"` или `"N кадров"`

- [ ] **Step 1: Установить pytest и создать конфиг**

```bash
venv_new/Scripts/python.exe -m pip install "pytest>=8"
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=8
```

`pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```

`tests/__init__.py` — пустой файл.

- [ ] **Step 2: Написать падающие тесты** — `tests/test_utils.py`:

```python
from datetime import datetime, timedelta

import pytest

from utils import (
    cooldown_left, fine_payload, fine_stars, fmt_cost, fmt_duration,
    is_quiz_passed, parse_amount, parse_fine_payload, parse_options,
    parse_years, start_decision,
)


# ── parse_years ──────────────────────────────────────────────────────────────

def test_parse_years_range():
    assert parse_years("1941-1945", max_year=2026) == [1941, 1942, 1943, 1944, 1945]


def test_parse_years_dashes_and_spaces():
    assert parse_years("1941 – 1942", max_year=2026) == [1941, 1942]
    assert parse_years("1941—1942", max_year=2026) == [1941, 1942]


def test_parse_years_mixed_dedup_sorted():
    assert parse_years("1943, 1939, 1941-1943", max_year=2026) == [1939, 1941, 1942, 1943]


def test_parse_years_single():
    assert parse_years("1942", max_year=2026) == [1942]


@pytest.mark.parametrize("bad", ["", "   ", "abc", "1945-1941", "1899", "2030", "41-45", "1941-", None])
def test_parse_years_errors(bad):
    with pytest.raises(ValueError):
        parse_years(bad, max_year=2026)


# ── parse_amount ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [("3", 3.0), ("2,5", 2.5), (" 0 ", 0.0), ("1.25", 1.25)])
def test_parse_amount_ok(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("bad", ["", "abc", "-1", "1.234", "nan", "inf", None])
def test_parse_amount_errors(bad):
    with pytest.raises(ValueError):
        parse_amount(bad)


# ── parse_options ────────────────────────────────────────────────────────────

def test_parse_options_ok():
    assert parse_options(" А \nБ\n\nВ\nГ ") == ["А", "Б", "В", "Г"]


@pytest.mark.parametrize("bad", ["А\nБ\nВ", "А\nБ\nВ\nГ\nД", "", None])
def test_parse_options_errors(bad):
    with pytest.raises(ValueError):
        parse_options(bad)


# ── Stars ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cost, stars", [(1, 5), (3, 15), (1.5, 8), (0.2, 1), (1.1, 6), (0.01, 1)])
def test_fine_stars(cost, stars):
    assert fine_stars(cost) == stars


def test_fine_payload_roundtrip():
    assert parse_fine_payload(fine_payload(12, 7)) == (12, 7)


@pytest.mark.parametrize("bad", ["", "fine:1", "x:1:2", "fine:a:2", None])
def test_parse_fine_payload_bad(bad):
    assert parse_fine_payload(bad) is None


# ── Тесты (обучение) ─────────────────────────────────────────────────────────

def test_is_quiz_passed_threshold():
    assert is_quiz_passed(8, 10) is True
    assert is_quiz_passed(7, 10) is False
    assert is_quiz_passed(20, 25) is True
    assert is_quiz_passed(19, 25) is False
    assert is_quiz_passed(0, 0) is False


def test_cooldown_left():
    now = datetime(2026, 9, 27, 12, 0)
    assert cooldown_left(None, now) is None
    assert cooldown_left(now - timedelta(hours=25), now) is None
    assert cooldown_left(now - timedelta(hours=24), now) is None
    assert cooldown_left(now - timedelta(hours=10), now) == timedelta(hours=14)


def test_fmt_duration():
    assert fmt_duration(timedelta(hours=13, minutes=20)) == "13 ч 20 мин"
    assert fmt_duration(timedelta(minutes=5)) == "5 мин"
    assert fmt_duration(timedelta(seconds=10)) == "1 мин"


def test_start_decision_order():
    now = datetime(2026, 9, 27, 12, 0)
    recent = now - timedelta(hours=1)
    assert start_decision(True, recent, 0, 5, now) == ("passed", None)
    assert start_decision(False, recent, 0, 5, now) == ("cooldown", timedelta(hours=23))
    assert start_decision(False, None, 4, 5, now) == ("no_points", None)
    assert start_decision(False, None, None, 0, now) == ("ok", None)
    assert start_decision(False, None, 5, 5, now) == ("ok", None)


def test_fmt_cost():
    assert fmt_cost(0) == "бесплатно"
    assert fmt_cost(None) == "бесплатно"
    assert fmt_cost(5) == "5 кадров"
    assert fmt_cost(2.5) == "2.5 кадров"
```

- [ ] **Step 3: Запустить — убедиться, что падает**

Run: `venv_new/Scripts/python.exe -m pytest tests/test_utils.py -v`
Expected: FAIL — `ImportError: cannot import name 'cooldown_left' from 'utils'`

- [ ] **Step 4: Реализовать** — в начало `utils.py` добавить импорты:

```python
import math
import re
from datetime import datetime, timedelta
```

В конец `utils.py` дописать:

```python
# ── Константы обновления ─────────────────────────────────────────────────────

STARS_PER_CADR = 5
PASS_RATIO = 0.8
TEST_COOLDOWN = timedelta(hours=24)

YEAR_HINT = "Например: 1941-1945 или 1939, 1941-1943"


# ── Парсинг ввода ────────────────────────────────────────────────────────────

def parse_years(text, min_year: int = 1900, max_year: int = None) -> list:
    """«1939, 1941-1943» → [1939, 1941, 1942, 1943]. Ошибка — ValueError с текстом для пользователя."""
    max_year = max_year or datetime.now().year
    years = set()
    for part in str(text or "").split(","):
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r"(\d{4})\s*[-–—]\s*(\d{4})", part)
        if match:
            start, end = int(match[1]), int(match[2])
            if start > end:
                raise ValueError(f"В диапазоне «{part}» начало больше конца.")
        elif re.fullmatch(r"\d{4}", part):
            start = end = int(part)
        else:
            raise ValueError(f"Не понимаю «{part}». {YEAR_HINT}")
        for year in (start, end):
            if not min_year <= year <= max_year:
                raise ValueError(f"Год {year} вне диапазона {min_year}–{max_year}.")
        years.update(range(start, end + 1))
    if not years:
        raise ValueError(f"Не указано ни одного года. {YEAR_HINT}")
    return sorted(years)


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


def parse_options(text) -> list:
    """Ровно 4 непустые строки — варианты ответа."""
    options = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if len(options) != 4:
        raise ValueError(f"Нужно ровно 4 варианта, каждый с новой строки (сейчас {len(options)}).")
    return options


# ── Оплата штрафов ───────────────────────────────────────────────────────────

def fine_stars(cost) -> int:
    """Стоимость штрафа в звёздах: 1 кадр = 5 ⭐, округление вверх."""
    return max(1, math.ceil(round(float(cost) * STARS_PER_CADR, 6)))


def fine_payload(fine_id: int, user_id: int) -> str:
    return f"fine:{fine_id}:{user_id}"


def parse_fine_payload(payload):
    parts = str(payload or "").split(":")
    if len(parts) != 3 or parts[0] != "fine":
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


# ── Обучение ─────────────────────────────────────────────────────────────────

def is_quiz_passed(correct: int, total: int) -> bool:
    return total > 0 and correct / total >= PASS_RATIO


def cooldown_left(last_fail_at, now):
    """Сколько осталось ждать после неудачной попытки; None — ждать не нужно."""
    if last_fail_at is None:
        return None
    left = last_fail_at + TEST_COOLDOWN - now
    return left if left > timedelta(0) else None


def fmt_duration(delta) -> str:
    minutes = max(1, math.ceil(delta.total_seconds() / 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч {minutes} мин" if hours else f"{minutes} мин"


def start_decision(passed: bool, last_fail_at, points, cost, now):
    """Можно ли начать тест: ('passed'|'cooldown'|'no_points'|'ok', остаток кулдауна)."""
    if passed:
        return "passed", None
    left = cooldown_left(last_fail_at, now)
    if left:
        return "cooldown", left
    if (points or 0) < (cost or 0):
        return "no_points", None
    return "ok", None


def fmt_cost(cost) -> str:
    return "бесплатно" if not cost else f"{fmt_points(cost)} кадров"
```

- [ ] **Step 5: Запустить тесты**

Run: `venv_new/Scripts/python.exe -m pytest tests/test_utils.py -v`
Expected: все PASS

- [ ] **Step 6: Commit**

```bash
git add pytest.ini requirements-dev.txt tests/__init__.py tests/test_utils.py utils.py
git commit -m "feat: add pure helpers for years, amounts, stars and quiz logic

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Модели и миграция БД

**Files:**
- Modify: `database/models.py`
- Create: `database/migrate.py`, `tests/test_migrate.py`

**Interfaces:**
- Produces:
  - `User.is_banned: bool`, `User.onboarded: bool`, `User.fine` становится `nullable=True` (legacy, не используется)
  - `UserReward.issued: bool`
  - `Battle.map_media_type: str | None` (`"photo"` / `"animation"`)
  - Модели `Fine`, `TrainingTest`, `TrainingQuestion`, `TrainingAttempt` (поля ниже)
  - `database.migrate.migrate(conn)` — синхронная, принимает sync `Connection`; вызывается через `conn.run_sync(migrate)`

- [ ] **Step 1: Написать падающие тесты** — `tests/test_migrate.py`:

```python
from sqlalchemy import create_engine, inspect, text

from database.migrate import migrate
from database.models import Base

OLD_SCHEMA = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, tg_id BIGINT, "
    "status VARCHAR, points FLOAT, fine VARCHAR)",
    "CREATE TABLE userrewards (id INTEGER PRIMARY KEY, user_id INTEGER, "
    "reward_id INTEGER, created_at DATETIME)",
    "CREATE TABLE battles (id INTEGER PRIMARY KEY, name VARCHAR, front VARCHAR, "
    "date_str VARCHAR, description VARCHAR, map_photo_id VARCHAR, equipment_text VARCHAR)",
]


def make_old_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        for ddl in OLD_SCHEMA:
            conn.execute(text(ddl))
        conn.execute(text(
            "INSERT INTO users (id, name, tg_id, status, points, fine) VALUES "
            "(1, 'A', 11, 'base_user', 5, 'Опоздал'), "
            "(2, 'B', 22, 'base_user', 0, NULL), "
            "(3, 'C', 33, 'base_user', 0, '   ')"
        ))
        conn.execute(text(
            "INSERT INTO userrewards (id, user_id, reward_id, created_at) "
            "VALUES (1, 1, 1, '2026-01-01 00:00:00')"
        ))
    return engine


def run_startup(engine):
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        migrate(conn)


def columns(engine, table):
    return {c["name"] for c in inspect(engine).get_columns(table)}


def test_adds_missing_columns_with_defaults_for_old_rows(tmp_path):
    engine = make_old_db(tmp_path)
    run_startup(engine)

    assert {"is_banned", "onboarded"} <= columns(engine, "users")
    assert "issued" in columns(engine, "userrewards")
    assert "map_media_type" in columns(engine, "battles")
    with engine.connect() as conn:
        assert tuple(conn.execute(text("SELECT is_banned, onboarded FROM users WHERE id = 1")).one()) == (0, 1)
        assert conn.execute(text("SELECT issued FROM userrewards WHERE id = 1")).scalar() == 1


def test_moves_legacy_fines_once(tmp_path):
    engine = make_old_db(tmp_path)
    run_startup(engine)
    run_startup(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT user_id, description, cost, status FROM fines")).all()
    assert [tuple(r) for r in rows] == [(1, "Опоздал", 0, "active")]


def test_fresh_database_is_fine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'new.db'}")
    run_startup(engine)
    run_startup(engine)
    assert {"is_banned", "onboarded"} <= columns(engine, "users")
    assert {"tests", "test_questions", "test_attempts", "fines"} <= set(inspect(engine).get_table_names())
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `venv_new/Scripts/python.exe -m pytest tests/test_migrate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'database.migrate'`

- [ ] **Step 3: Обновить модели** — в `database/models.py`:

В классе `User` заменить строку `fine: Mapped[str] = mapped_column()` на:
```python
    fine: Mapped[str] = mapped_column(nullable=True)  # legacy: штрафы теперь в таблице fines
    is_banned: Mapped[bool] = mapped_column(default=False)
    onboarded: Mapped[bool] = mapped_column(default=False)
```

В классе `UserReward` после `created_at` добавить:
```python
    issued: Mapped[bool] = mapped_column(default=False)
```

В классе `Battle` после `map_photo_id` добавить:
```python
    map_media_type: Mapped[str] = mapped_column(nullable=True)  # photo | animation
```

Перед `async def async_main()` добавить модели:
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
    closed_by = mapped_column(BigInteger, nullable=True)  # tg_id админа, снявшего штраф
    paid_with: Mapped[str] = mapped_column(nullable=True)  # cadrs | stars
    stars_amount: Mapped[int] = mapped_column(nullable=True)
    charge_id: Mapped[str] = mapped_column(nullable=True)  # telegram_payment_charge_id


class TrainingTest(Base):
    __tablename__ = 'tests'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    cost: Mapped[float] = mapped_column(default=0.0)


class TrainingQuestion(Base):
    __tablename__ = 'test_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey('tests.id', ondelete="CASCADE"))
    position: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column()
    option_1: Mapped[str] = mapped_column()
    option_2: Mapped[str] = mapped_column()
    option_3: Mapped[str] = mapped_column()
    option_4: Mapped[str] = mapped_column()
    correct: Mapped[int] = mapped_column()  # 1..4


class TrainingAttempt(Base):
    __tablename__ = 'test_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    test_id: Mapped[int] = mapped_column(ForeignKey('tests.id', ondelete="CASCADE"))
    correct_count: Mapped[int] = mapped_column()
    total: Mapped[int] = mapped_column()
    passed: Mapped[bool] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

- [ ] **Step 4: Создать `database/migrate.py`**

```python
"""Идемпотентная миграция SQLite при старте.

create_all создаёт только новые таблицы, но не добавляет колонки в существующие.
Здесь добавляем недостающие колонки (DEFAULT задаёт значение для уже
существующих строк) и один раз переносим старые текстовые штрафы.
"""
from sqlalchemy import text

# (таблица, колонка, DDL). DEFAULT — значение для строк, которые уже есть в БД;
# новые строки получают значение по умолчанию из модели.
COLUMNS = [
    ("users", "is_banned", "BOOLEAN NOT NULL DEFAULT 0"),
    ("users", "onboarded", "BOOLEAN NOT NULL DEFAULT 1"),  # старые юзеры приветствие уже не получают
    ("userrewards", "issued", "BOOLEAN NOT NULL DEFAULT 1"),  # старые награды считаются выданными
    ("battles", "map_media_type", "VARCHAR"),
]


def migrate(conn) -> None:
    for table, column, ddl in COLUMNS:
        existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        if existing and column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
    _move_legacy_fines(conn)


def _move_legacy_fines(conn) -> None:
    """users.fine → fines (active, cost 0) для тех, у кого ещё нет записей в fines."""
    conn.execute(text(
        "INSERT INTO fines (user_id, description, cost, status, created_at) "
        "SELECT u.id, TRIM(u.fine), 0, 'active', CURRENT_TIMESTAMP FROM users u "
        "WHERE u.fine IS NOT NULL AND TRIM(u.fine) != '' "
        "AND NOT EXISTS (SELECT 1 FROM fines f WHERE f.user_id = u.id)"
    ))
```

- [ ] **Step 5: Подключить миграцию при старте** — в `database/models.py` заменить `async_main`:

```python
async def async_main():
    from database.migrate import migrate

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(migrate)
```

- [ ] **Step 6: Запустить тесты**

Run: `venv_new/Scripts/python.exe -m pytest tests -v`
Expected: все PASS

- [ ] **Step 7: Проверить на копии боевой БД**

```bash
venv_new/Scripts/python.exe - <<'EOF'
import os, tempfile, shutil
from sqlalchemy import create_engine, inspect, text
from database.models import Base
from database.migrate import migrate
path = os.path.join(tempfile.gettempdir(), "eventbot_db_copy.sqlite3")
shutil.copy("db.sqlite3", path)
engine = create_engine(f"sqlite:///{path}")
for _ in range(2):
    with engine.begin() as conn:
        Base.metadata.create_all(conn)
        migrate(conn)
with engine.connect() as conn:
    print("users cols:", [c["name"] for c in inspect(engine).get_columns("users")])
    print("fines:", conn.execute(text("SELECT count(*) FROM fines")).scalar())
    print("legacy fines:", conn.execute(text("SELECT count(*) FROM users WHERE fine IS NOT NULL AND TRIM(fine) != ''")).scalar())
    print("onboarded=1:", conn.execute(text("SELECT count(*) FROM users WHERE onboarded = 1")).scalar(), "of", conn.execute(text("SELECT count(*) FROM users")).scalar())
EOF
```
Expected: колонки `is_banned`, `onboarded` есть; `fines` == `legacy fines`; все пользователи `onboarded = 1`. Оригинальный `db.sqlite3` не изменён (`git status db.sqlite3` не показывает новых изменений от этого шага — если файл уже был modified до начала работ, это нормально, просто не добавлять его).

- [ ] **Step 8: Commit**

```bash
git add database/models.py database/migrate.py tests/test_migrate.py
git commit -m "feat: add models for fines, training and flags with startup migration

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Годы танка диапазоном

**Files:**
- Modify: `handlers/usercommands.py` (обработчики `process_tank_years` ~стр. 824, `process_new_years` ~стр. 1119, подсказки ~стр. 816, 994, 1049, 1262)

**Interfaces:**
- Consumes: `utils.parse_years(text) -> list[int]` (ValueError с текстом), `utils.YEAR_HINT`

- [ ] **Step 1: Импорт** — в `handlers/usercommands.py` строку `from utils import cadr_message` заменить на:

```python
from utils import cadr_message, parse_years, YEAR_HINT
```

- [ ] **Step 2: Подсказка шага 4 при добавлении** — в `process_tank_type` заменить текст ответа:

```python
    await message.answer(
        "✅ Тип сохранен!\n\n"
        "📅 Шаг 4/6: Введите годы использования танка:\n"
        f"<i>{YEAR_HINT}</i>",
        parse_mode="HTML"
    )
```

- [ ] **Step 3: Заменить тело `process_tank_years`** целиком:

```python
@user.message(TankStates.waiting_tank_years)
async def process_tank_years(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.clear()
        return
    try:
        valid_years = parse_years(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\nВведите годы ещё раз:")
        return

    await state.update_data(years=valid_years)
    await message.answer(
        f"✅ Годы сохранены: {', '.join(map(str, valid_years))}\n\n"
        "📄 Шаг 5/6: Введите описание танка:",
        parse_mode="HTML"
    )
    await state.set_state(TankStates.waiting_tank_description)
```

- [ ] **Step 4: Заменить тело `process_new_years`** целиком:

```python
@user.message(TankStates.waiting_new_years)
async def process_new_years(message: Message, state: FSMContext):
    if message.text == "отмена":
        await state.set_state(TankStates.nothing)
        return
    data = await state.get_data()
    tank = data.get('selected_tank')
    choices = data.get('edit_choices', [])

    try:
        valid_years = parse_years(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\nВведите годы ещё раз:")
        return

    success = await update_tank_years(tank.id, valid_years)
    if success:
        await process_remaining_edits(message, state, choices, 4, f"✅ Годы танка обновлены: {', '.join(map(str, valid_years))}")
    else:
        await message.answer("❌ Не удалось обновить годы танка.")
        await state.clear()
```

- [ ] **Step 5: Остальные подсказки**
  - `"4. 📅 Годы (через запятую)\n"` → `"4. 📅 Годы\n"`
  - `"Введите новые годы через запятую:",` → `f"Введите новые годы. {YEAR_HINT}:",`
  - `f"📅 Введите новые годы создания танка через запятую\nТекущие: {years_str}:",` → `f"📅 Введите новые годы использования танка ({YEAR_HINT})\nТекущие: {years_str}:",`
  - Строки `"🔢 <b>Введите номера через запятую:</b>"` и `"⚠️ Неверный формат. Введите номера через запятую:"` — **не трогать** (это выбор полей, не годы).

- [ ] **Step 6: Проверить импорт модуля и тесты**

Run: `venv_new/Scripts/python.exe -c "import handlers" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: без ошибок импорта, тесты PASS. `grep -n "через запятую" handlers/usercommands.py` показывает только две строки про номера полей.

- [ ] **Step 7: Commit**

```bash
git add handlers/usercommands.py
git commit -m "feat: accept tank years as ranges like 1941-1945

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: GIF-карты сражений

**Files:**
- Modify: `handlers/admin_battles.py` (шаг 4 создания ~стр. 95–122, подсказки ~стр. 348, 367, редактирование ~стр. 434–441, сохранение ~стр. 151)
- Modify: `handlers/battles.py` (`show_battle_detail` ~стр. 150)
- Modify: `database/requests.py` (`create_battle`)

**Interfaces:**
- Produces: `create_battle(..., map_photo_id=None, map_media_type=None, equipment_text=None)`; `admin_battles.map_media(message) -> tuple[str, str]`

- [ ] **Step 1: `create_battle` принимает тип** — в `database/requests.py` сигнатура и конструктор:

```python
async def create_battle(
    name: str,
    front: str,
    date_str: str,
    description: str,
    map_photo_id: str = None,
    equipment_text: str = None,
    map_media_type: str = None,
) -> bool:
    async with async_session() as session:
        try:
            battle = Battle(
                name=name,
                front=front,
                date_str=date_str,
                description=description,
                map_photo_id=map_photo_id,
                map_media_type=map_media_type,
                equipment_text=equipment_text,
            )
```
(остальное тело без изменений)

- [ ] **Step 2: Хелпер и шаг 4 создания** — в `handlers/admin_battles.py` после определения классов состояний добавить:

```python
def map_media(message: Message) -> tuple:
    """(file_id, тип) для карты: GIF приходит как animation, картинка — как photo."""
    if message.animation:
        return message.animation.file_id, "animation"
    return message.photo[-1].file_id, "photo"
```

Заменить обработчики шага 4:

```python
@admin_battles.message(CreateBattle.map_photo, F.photo | F.animation)
async def get_battle_map(message: Message, state: FSMContext):
    file_id, media_type = map_media(message)
    await state.update_data(map_photo_id=file_id, map_media_type=media_type)
    await message.answer(
        "✅ Карта сохранена!\n\n"
        "Шаг 5/6: Введите описание сражения (история, план боя и т.д.):"
    )
    await state.set_state(CreateBattle.description)


@admin_battles.message(CreateBattle.map_photo)
async def wrong_map_format(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте фото или GIF (карту сражения):")
```

В подсказке шага 3→4: `"Шаг 4/6: Отправьте карту сражения (фото):"` → `"Шаг 4/6: Отправьте карту сражения (фото или GIF):"`.

В вызове `create_battle(...)` в `get_battle_equipment` добавить аргумент `map_media_type=data.get("map_media_type"),`.

- [ ] **Step 3: Редактирование карты**

```python
@admin_battles.message(EditBattle.new_map, F.photo | F.animation)
async def edit_new_map(message: Message, state: FSMContext):
    file_id, media_type = map_media(message)
    await _apply_edit(message, state, map_photo_id=file_id, map_media_type=media_type)


@admin_battles.message(EditBattle.new_map)
async def edit_new_map_wrong(message: Message):
    await message.answer("Пожалуйста, отправьте фото или GIF (карту):")
```

Подсказки: `"4 — Карту (фото)\n"` → `"4 — Карту (фото или GIF)\n"`; `"4": "Отправьте новую карту (фото):",` → `"4": "Отправьте новую карту (фото или GIF):",`.

- [ ] **Step 4: Показ карты** — в `handlers/battles.py`, `show_battle_detail`:

```python
    photo_msg_id = 0
    if battle.map_photo_id:
        if battle.map_media_type == "animation":
            sent = await callback.message.answer_animation(animation=battle.map_photo_id)
        else:
            sent = await callback.message.answer_photo(photo=battle.map_photo_id)
        photo_msg_id = sent.message_id
```

- [ ] **Step 5: Проверить**

Run: `venv_new/Scripts/python.exe -c "import handlers" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: без ошибок, тесты PASS.

- [ ] **Step 6: Commit**

```bash
git add handlers/admin_battles.py handlers/battles.py database/requests.py
git commit -m "feat: allow GIF animations as battle maps

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Приветствие после регистрации, `/menu`, правила

**Files:**
- Modify: `handlers/start.py`, `handlers/usercommands.py` (`menu`, текст правил), `database/requests.py`
- Test: `tests/conftest.py` (создать), `tests/test_requests_users.py` (создать)

**Interfaces:**
- Produces: `database.requests.set_onboarded(tg_id) -> None`; `handlers.start.WELCOME_TEXT`; callback `"onboard_ok"`; фикстуры `db` и `make_user` в `tests/conftest.py`

- [ ] **Step 1: Фикстуры временной БД** — `tests/conftest.py`:

```python
import asyncio
import importlib

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database.models import Base, User

# Модули, у которых подменяем async_session на временную БД.
# Модуль, которого ещё нет (создаётся в поздних задачах), пропускается.
DB_MODULES = ("database.requests", "database.fines", "database.training")


@pytest.fixture
def db(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", poolclass=NullPool)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init())
    for name in DB_MODULES:
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError:
            continue
        monkeypatch.setattr(module, "async_session", session_maker)
    yield session_maker
    asyncio.run(engine.dispose())


@pytest.fixture
def make_user(db):
    def _make(name="A", tg_id=1, status="base_user", points=0.0, **extra) -> int:
        async def go():
            async with db() as session:
                user = User(name=name, tg_id=tg_id, status=status, points=points, **extra)
                session.add(user)
                await session.commit()
                return user.id
        return asyncio.run(go())
    return _make
```

- [ ] **Step 2: Падающий тест** — `tests/test_requests_users.py`:

```python
import asyncio

from database import requests as r


def test_set_onboarded(make_user):
    make_user(tg_id=100, onboarded=False)
    asyncio.run(r.set_onboarded(100))
    assert asyncio.run(r.get_user(100)).onboarded is True


def test_new_user_is_not_onboarded(db):
    asyncio.run(r.set_user(200))
    user = asyncio.run(r.get_user(200))
    assert user.onboarded is False
    assert user.is_banned is False
```

Run: `venv_new/Scripts/python.exe -m pytest tests/test_requests_users.py -v`
Expected: FAIL — `AttributeError: module 'database.requests' has no attribute 'set_onboarded'`

- [ ] **Step 3: `set_onboarded`** — в `database/requests.py` после `set_name_user`:

```python
async def set_onboarded(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.onboarded = True
            await session.commit()
```

Run: `venv_new/Scripts/python.exe -m pytest tests -v` → PASS.

- [ ] **Step 4: Приветствие** — `handlers/start.py`.

Импорты заменить на:
```python
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram import Router
from aiogram import F
from keyboards import userboard, adminboard
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from database.requests import set_user, set_status, set_name_user, get_user, check_name_exists, set_onboarded
```

После `array_exchange = [...]` добавить:
```python
WELCOME_TEXT = (
    "📖 Как читать обозначения в боте:\n\n"
    "Pz. III A (Pz. III E)\n"
    "Официальное название техники (аналогичное название в игре).\n\n"
    "(Ред.) — техника или сражение сейчас редактируется.\n\n"
    "Если бот перестал отвечать после его удаления/перезапуска, "
    "напиши команду /menu — интерфейс восстановится."
)

ONBOARD_CALLBACK = "onboard_ok"
onboard_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Понятно!", callback_data=ONBOARD_CALLBACK)]
])


async def send_welcome(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=onboard_kb)
```

В `start_command` заменить
```python
    if data.name != None:
        return
```
на
```python
    if data.name is not None:
        if not data.onboarded:
            await send_welcome(message)
        return
```

В `set_name_to_user` заменить хвост после `await state.clear()` (последние строки функции):
```python
    await set_name_user(message.from_user.id, new_nick)
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user.onboarded:
        await message.answer(f'✅ Ваш ник "{new_nick}" успешно сохранён', reply_markup=ReplyKeyboardRemove())
        await send_welcome(message)
        return
    await message.answer(f'✅ Ваш ник "{new_nick}" успешно сохранён',
                         reply_markup=await board_for(message.from_user.id))
```

Перед `cancel_accept` добавить:
```python
@start.callback_query(F.data == ONBOARD_CALLBACK)
async def onboard_ok(callback: CallbackQuery):
    await set_onboarded(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Меню открыто 👇", reply_markup=await board_for(callback.from_user.id))
    await callback.answer()
```

- [ ] **Step 5: `/menu`** — в `handlers/usercommands.py` заменить функцию `menu`:

```python
@user.message(Command('menu'))
async def menu(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user.name:
        await message.answer('Сначала зарегистрируйся: /start')
        return
    await message.answer('Меню', reply_markup=adminboard if user.status == 'admin' else userboard)
```

- [ ] **Step 6: Правила** — в тексте правил заменить `"  - Участникам клана [Т-70В]\n"` на `"  - Участникам кланов [Т-70В] и [RENWA]\n"`.

- [ ] **Step 7: Проверить**

Run: `venv_new/Scripts/python.exe -c "import handlers" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add handlers/start.py handlers/usercommands.py database/requests.py tests/conftest.py tests/test_requests_users.py
git commit -m "feat: onboarding message after registration, fix /menu, add RENWA to rules

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Этап 2 — штрафы, блокировка, оплата

### Task 6: Запросы к таблице штрафов

**Files:**
- Create: `database/fines.py`, `tests/test_fines_db.py`

**Interfaces:**
- Consumes: `database.models.Fine`, `User`, `UserEvent`, `async_session`
- Produces (`database/fines.py`):
  - `add_fine(user_id: int, description: str, cost: float) -> Fine | None`
  - `get_fine(fine_id: int) -> Fine | None`
  - `get_active_fines(user_id: int) -> list[Fine]` (по `created_at`, `id`)
  - `get_users_with_active_fines(event_id: int | None = None) -> list[tuple[User, list[Fine]]]` (по имени)
  - `remove_fine(fine_id: int, admin_tg_id: int) -> bool`
  - `pay_fine_with_cadrs(fine_id: int, user_id: int) -> str` — `"ok" | "not_found" | "not_active" | "free" | "no_points"`
  - `mark_fine_paid_stars(fine_id: int, stars: int, charge_id: str) -> bool`

- [ ] **Step 1: Падающие тесты** — `tests/test_fines_db.py`:

```python
import asyncio

from database import fines as f
from database.models import UserEvent


def run(coro):
    return asyncio.run(coro)


def test_add_and_list_active(make_user):
    uid = make_user(points=10)
    fine = run(f.add_fine(uid, "Опоздал", 3))
    assert fine.id and fine.status == "active" and fine.cost == 3
    assert [x.id for x in run(f.get_active_fines(uid))] == [fine.id]


def test_add_fine_unknown_user(db):
    assert run(f.add_fine(999, "x", 1)) is None


def test_remove_keeps_history(make_user):
    uid = make_user()
    fine = run(f.add_fine(uid, "x", 1))
    assert run(f.remove_fine(fine.id, admin_tg_id=555)) is True
    assert run(f.remove_fine(fine.id, admin_tg_id=555)) is False
    stored = run(f.get_fine(fine.id))
    assert stored.status == "removed" and stored.closed_by == 555 and stored.closed_at
    assert run(f.get_active_fines(uid)) == []


def test_pay_with_cadrs(make_user):
    uid = make_user(points=10)
    fine = run(f.add_fine(uid, "x", 3))
    assert run(f.pay_fine_with_cadrs(fine.id, uid)) == "ok"
    stored = run(f.get_fine(fine.id))
    assert stored.status == "paid" and stored.paid_with == "cadrs"
    from database.requests import get_user_by_id
    assert run(get_user_by_id(uid)).points == 7
    assert run(f.pay_fine_with_cadrs(fine.id, uid)) == "not_active"


def test_pay_with_cadrs_errors(make_user):
    poor = make_user(name="P", tg_id=2, points=1)
    other = make_user(name="O", tg_id=3, points=100)
    costly = run(f.add_fine(poor, "x", 3))
    free = run(f.add_fine(poor, "legacy", 0))
    assert run(f.pay_fine_with_cadrs(costly.id, poor)) == "no_points"
    assert run(f.pay_fine_with_cadrs(free.id, poor)) == "free"
    assert run(f.pay_fine_with_cadrs(costly.id, other)) == "not_found"
    assert run(f.pay_fine_with_cadrs(9999, poor)) == "not_found"
    assert run(f.get_fine(costly.id)).status == "active"


def test_mark_paid_stars_once(make_user):
    uid = make_user()
    fine = run(f.add_fine(uid, "x", 2))
    assert run(f.mark_fine_paid_stars(fine.id, 10, "ch_1")) is True
    assert run(f.mark_fine_paid_stars(fine.id, 10, "ch_2")) is False
    stored = run(f.get_fine(fine.id))
    assert (stored.status, stored.paid_with, stored.stars_amount, stored.charge_id) == ("paid", "stars", 10, "ch_1")


def test_users_with_active_fines_grouped_and_by_event(db, make_user):
    a = make_user(name="Бета", tg_id=1)
    b = make_user(name="Альфа", tg_id=2)
    make_user(name="Чистый", tg_id=3)
    run(f.add_fine(a, "a1", 1))
    run(f.add_fine(a, "a2", 1))
    removed = run(f.add_fine(b, "b1", 1))
    run(f.add_fine(b, "b2", 1))
    run(f.remove_fine(removed.id, 1))

    rows = run(f.get_users_with_active_fines())
    assert [(u.name, [x.description for x in fs]) for u, fs in rows] == [("Альфа", ["b2"]), ("Бета", ["a1", "a2"])]

    async def join_event():
        async with db() as session:
            session.add_all([UserEvent(user_id=a, event_id=7), UserEvent(user_id=a, event_id=7)])
            await session.commit()
    run(join_event())
    rows = run(f.get_users_with_active_fines(event_id=7))
    assert [(u.name, len(fs)) for u, fs in rows] == [("Бета", 2)]
```

Run: `venv_new/Scripts/python.exe -m pytest tests/test_fines_db.py -v`
Expected: FAIL — `ImportError: cannot import name 'fines' from 'database'`

- [ ] **Step 2: Реализовать** — `database/fines.py`:

```python
"""Матч-штрафы: выдача, снятие, оплата. Записи не удаляются — это история."""
from datetime import datetime

from sqlalchemy import select, update

from database.models import Fine, User, UserEvent, async_session


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
            select(Fine)
            .where(Fine.user_id == user_id, Fine.status == "active")
            .order_by(Fine.created_at, Fine.id)
        )
        return list(result.all())


async def get_users_with_active_fines(event_id: int = None) -> list:
    """[(User, [Fine, ...]), ...] — только игроки с ником и активными штрафами."""
    stmt = (
        select(User, Fine)
        .join(Fine, Fine.user_id == User.id)
        .where(Fine.status == "active", User.name.isnot(None))
        .order_by(User.name, Fine.created_at, Fine.id)
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
    """'ok' | 'not_found' | 'not_active' | 'free' | 'no_points'."""
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

        # Условный UPDATE защищает от двойного нажатия: второй запрос не найдёт active
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
```

- [ ] **Step 3: Запустить тесты**

Run: `venv_new/Scripts/python.exe -m pytest tests -v`
Expected: все PASS

- [ ] **Step 4: Commit**

```bash
git add database/fines.py tests/test_fines_db.py
git commit -m "feat: fines table queries with history, cadr and stars payment

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: `handlers/fines.py` — перенос матч-штрафов, штраф со стоимостью, снятие

**Контекст:** в `handlers/admin.py` `admin = Router()` объявлен дважды (стр. 17 и 232). Обработчики первой половины файла (создание ивента) висят на первом роутере, который нигде не подключён, — это мёртвый код (живое создание ивента — в `handlers/events.py`). Экспортируется второй роутер с кодом штрафов. Поэтому `handlers/admin.py` **удаляется целиком**, код штрафов переписывается в `handlers/fines.py`. Нельзя оставлять первую половину файла: она «оживёт» и перехватит кнопку «Добавить ивент».

**Files:**
- Create: `handlers/fines.py`
- Delete: `handlers/admin.py`
- Modify: `handlers/__init__.py`

**Interfaces:**
- Consumes: `database.fines.*` (Task 6), `utils.parse_amount`, `utils.fmt_points`
- Produces (используются в Task 8 и 10):
  - `fines_router`, `FINES_BUTTONS = ("Матч-штрафы", "матч-штрафы")`
  - `FineAdminCb(action: str, user_id: int)`, `FineStates`, `BackCb`
  - `render_admin_user(user) -> str` (async), `kb_admin_user_actions(user)` — принимает объект `User`
  - `send_admin_card(message, user, prefix="")` (async), `deny_non_admin(message, state) -> bool` (async)

- [ ] **Step 1: Создать `handlers/fines.py`**

```python
"""Матч-штрафы: поиск игроков, карточка игрока для админа, штрафы и очки."""
from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.fines import add_fine, get_active_fines, get_users_with_active_fines, remove_fine
from database.requests import (
    decrease_user_points,
    get_all_events,
    get_all_users_ordered,
    get_event_by_index,
    get_event_participants,
    get_user_by_id,
    get_user_by_name,
    is_admin,
    reset_user_points,
    set_user_points_value,
)
from utils import fmt_points, parse_amount

fines_router = Router()

FINES_BUTTONS = ("Матч-штрафы", "матч-штрафы")  # второй — со старых клавиатур
NO_FINES_TEXT = "Игроки с штрафом отсутствуют"


# ---------- CallbackData ----------

class FineMenuCb(CallbackData, prefix="fine_menu"):
    action: str  # all | event | nick


class FineAdminCb(CallbackData, prefix="fine_adm"):
    action: str  # card | points_zero | points_set | points_dec | fine_add | fines_list
    user_id: int


class FineRemoveCb(CallbackData, prefix="fine_rm"):
    fine_id: int
    user_id: int


class BackCb(CallbackData, prefix="back"):
    target: str  # to_main


# ---------- FSM ----------

class FineStates(StatesGroup):
    wait_event_number = State()
    wait_nick_search = State()
    wait_pick_user_number = State()
    wait_points_set_value = State()
    wait_points_dec_value = State()
    wait_fine_text = State()
    wait_fine_cost = State()


# ---------- Render ----------

def fine_line(fine) -> str:
    cost = f" — {fmt_points(fine.cost)} кадров" if fine.cost else ""
    return f"{fine.description}{cost}"


def render_public_fines(user, fines) -> str:
    return f"{user.name} — " + "; ".join(f.description for f in fines)


def render_public_list(rows) -> str:
    return "\n".join(f"{i}. {render_public_fines(u, fs)}" for i, (u, fs) in enumerate(rows, start=1))


async def render_admin_user(user) -> str:
    fines = await get_active_fines(user.id)
    lines = [
        f"Игрок: {user.name}",
        f"Очки: {fmt_points(user.points)}",
        f"Активных штрафов: {len(fines)}",
    ]
    if user.is_banned:
        lines.append("🚫 Заблокирован")
    if user.status is not None:
        lines.append(f"Статус: {user.status}")
    if user.tg_id is not None:
        lines.append(f"tg_id: {user.tg_id}")
    return "\n".join(lines)


def render_fines_list(user, fines) -> str:
    if not fines:
        return f"У игрока {user.name} нет активных штрафов."
    lines = [f"Активные штрафы {user.name}:"]
    lines += [f"{i}. {fine_line(f)}" for i, f in enumerate(fines, start=1)]
    return "\n".join(lines)


# ---------- Keyboards ----------

def kb_search_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="Все игроки", callback_data=FineMenuCb(action="all").pack())
    kb.button(text="По ивенту", callback_data=FineMenuCb(action="event").pack())
    kb.button(text="По нику", callback_data=FineMenuCb(action="nick").pack())
    kb.adjust(1)
    return kb.as_markup()


def kb_admin_user_actions(user):
    kb = InlineKeyboardBuilder()
    for text, action in (
        ("Обнулить очки", "points_zero"),
        ("Задать очки", "points_set"),
        ("Убавить очки", "points_dec"),
        ("Добавить штраф", "fine_add"),
        ("Штрафы игрока", "fines_list"),
    ):
        kb.button(text=text, callback_data=FineAdminCb(action=action, user_id=user.id).pack())
    kb.button(text="Назад", callback_data=BackCb(target="to_main").pack())
    kb.adjust(1)
    return kb.as_markup()


def kb_fines_list(user_id: int, fines):
    kb = InlineKeyboardBuilder()
    for i, fine in enumerate(fines, start=1):
        kb.button(text=f"Снять №{i}", callback_data=FineRemoveCb(fine_id=fine.id, user_id=user_id).pack())
    kb.button(text="◀️ К игроку", callback_data=FineAdminCb(action="card", user_id=user_id).pack())
    kb.adjust(1)
    return kb.as_markup()


# ---------- Helpers ----------

async def send_admin_card(message: Message, user, prefix: str = ""):
    await message.answer(prefix + await render_admin_user(user), reply_markup=kb_admin_user_actions(user))


async def deny_non_admin(message: Message, state: FSMContext) -> bool:
    """True — не админ, обработку надо прекратить."""
    if await is_admin(message.from_user.id):
        return False
    await state.clear()
    await message.answer("Доступно только администратору.")
    return True


# ---------- Entry ----------

@fines_router.message(F.text.in_(FINES_BUTTONS))
async def fine_entry(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("режим поиска", reply_markup=kb_search_menu())


@fines_router.callback_query(BackCb.filter(F.target == "to_main"))
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("режим поиска", reply_markup=kb_search_menu())
    await callback.answer()


# ---------- Menu: ALL ----------

@fines_router.callback_query(FineMenuCb.filter(F.action == "all"))
async def mode_all(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    if await is_admin(callback.from_user.id):
        users = await get_all_users_ordered()
        if not users:
            await callback.message.answer("Пользователей нет.")
            await callback.answer()
            return
        await state.set_state(FineStates.wait_pick_user_number)
        await state.update_data(pick_ids=[u.id for u in users])
        lines = [f"{i}. {u.name} (очки: {fmt_points(u.points)})" for i, u in enumerate(users, start=1)]
        await callback.message.answer("\n".join(lines) + "\n\nВведи номер игрока:")
        await callback.answer()
        return

    rows = await get_users_with_active_fines()
    await callback.message.answer(render_public_list(rows) if rows else NO_FINES_TEXT)
    await callback.answer()


# ---------- Menu: EVENT ----------

@fines_router.callback_query(FineMenuCb.filter(F.action == "event"))
async def mode_event_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    events = await get_all_events()
    if not events:
        await callback.message.answer("Ивентов нет.")
        await callback.answer()
        return

    lines = []
    for i, e in enumerate(events, start=1):
        dt = e.time.strftime("%d.%m.%Y %H:%M") if getattr(e, "time", None) else ""
        lines.append(f"{i}. {e.name} {dt}".strip())

    await state.set_state(FineStates.wait_event_number)
    await state.update_data(events_count=len(events))
    await callback.message.answer("\n".join(lines) + "\n\nВведи номер ивента:")
    await callback.answer()


@fines_router.message(FineStates.wait_event_number)
async def mode_event_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        idx = int((message.text or "").strip())
    except ValueError:
        await message.answer("Нужно число (номер ивента).")
        return

    if idx < 1 or idx > data.get("events_count", 0):
        await message.answer("Неверный номер ивента.")
        return

    event = await get_event_by_index(idx)
    if not event:
        await message.answer("Ивент не найден.")
        await state.clear()
        return

    if await is_admin(message.from_user.id):
        users = await get_event_participants(event.id)
        if not users:
            await message.answer("Участников ивента нет.")
            await state.clear()
            return
        await state.set_state(FineStates.wait_pick_user_number)
        await state.update_data(pick_ids=[u.id for u in users])
        lines = [f"{i}. {u.name} (очки: {fmt_points(u.points)})" for i, u in enumerate(users, start=1)]
        await message.answer("\n".join(lines) + "\n\nВведи номер игрока:")
        return

    rows = await get_users_with_active_fines(event.id)
    await message.answer(render_public_list(rows) if rows else NO_FINES_TEXT)
    await state.clear()


# ---------- Menu: NICK ----------

@fines_router.callback_query(FineMenuCb.filter(F.action == "nick"))
async def mode_nick_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(FineStates.wait_nick_search)
    await callback.message.answer("Введи ник пользователя")
    await callback.answer()


@fines_router.message(FineStates.wait_nick_search)
async def mode_nick_apply(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user_by_name((message.text or "").strip())
    if not user:
        await message.answer("Нету игрока с таким ником")
        return

    if await is_admin(message.from_user.id):
        await send_admin_card(message, user)
        return

    fines = await get_active_fines(user.id)
    await message.answer(render_public_fines(user, fines) if fines else "Игрок не получал штрафов")


# ---------- Admin: pick user by number ----------

@fines_router.message(FineStates.wait_pick_user_number)
async def pick_user_number(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return

    ids = (await state.get_data()).get("pick_ids", [])
    try:
        idx = int((message.text or "").strip())
    except ValueError:
        await message.answer("Нужно число (номер игрока).")
        return
    if idx < 1 or idx > len(ids):
        await message.answer("Неверный номер.")
        return

    await state.clear()
    user = await get_user_by_id(ids[idx - 1])
    if not user:
        await message.answer("Игрок не найден.")
        return
    await send_admin_card(message, user)


# ---------- Admin buttons (безопасно для чужих нажатий) ----------

@fines_router.callback_query(FineAdminCb.filter())
async def admin_buttons(callback: CallbackQuery, callback_data: FineAdminCb, state: FSMContext):
    user = await get_user_by_id(callback_data.user_id)
    if not user:
        await callback.answer("Игрок не найден.", show_alert=True)
        return

    # Не админ нажал на кнопку из пересланного сообщения — только показываем штрафы
    if not await is_admin(callback.from_user.id):
        fines = await get_active_fines(user.id)
        if fines:
            await callback.message.answer(render_public_fines(user, fines))
            await callback.answer()
        else:
            await callback.answer("У игрока нет штрафов.", show_alert=True)
        return

    action = callback_data.action

    if action == "card":
        await callback.message.edit_text(await render_admin_user(user), reply_markup=kb_admin_user_actions(user))
        await callback.answer()
        return

    if action == "points_zero":
        await reset_user_points(user.id)
        user = await get_user_by_id(user.id)
        await callback.message.edit_text(
            "✅ Очки обнулены.\n\n" + await render_admin_user(user),
            reply_markup=kb_admin_user_actions(user),
        )
        await callback.answer()
        return

    if action in ("points_set", "points_dec"):
        await state.set_state(FineStates.wait_points_set_value if action == "points_set" else FineStates.wait_points_dec_value)
        await state.update_data(target_user_id=user.id)
        prompt = ("Введи число. Очки пользователя станут равны этому числу:" if action == "points_set"
                  else "Введи число. На столько очков будет уменьшено:")
        await callback.message.answer(prompt)
        await callback.answer()
        return

    if action == "fine_add":
        await state.set_state(FineStates.wait_fine_text)
        await state.update_data(target_user_id=user.id)
        await callback.message.answer(f"Введи описание штрафа для {user.name}:")
        await callback.answer()
        return

    if action == "fines_list":
        fines = await get_active_fines(user.id)
        await callback.message.answer(render_fines_list(user, fines), reply_markup=kb_fines_list(user.id, fines))
        await callback.answer()
        return

    await callback.answer("Неизвестное действие.", show_alert=True)


# ---------- Admin: remove fine ----------

@fines_router.callback_query(FineRemoveCb.filter())
async def fine_remove(callback: CallbackQuery, callback_data: FineRemoveCb):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступно только администратору.", show_alert=True)
        return

    if not await remove_fine(callback_data.fine_id, callback.from_user.id):
        await callback.answer("Штраф уже закрыт.", show_alert=True)
    else:
        await callback.answer("✅ Штраф снят")

    user = await get_user_by_id(callback_data.user_id)
    if not user:
        return
    fines = await get_active_fines(user.id)
    await callback.message.edit_text(render_fines_list(user, fines), reply_markup=kb_fines_list(user.id, fines))


# ---------- Admin: points set/dec apply ----------

@fines_router.message(FineStates.wait_points_set_value)
async def points_set_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    try:
        value = parse_amount(message.text)
    except ValueError as e:
        await message.answer(str(e))
        return

    user_id = (await state.get_data()).get("target_user_id")
    await state.clear()
    await set_user_points_value(user_id, value)
    user = await get_user_by_id(user_id)
    await send_admin_card(message, user, f"✅ Очки установлены на {fmt_points(value)}.\n\n")


@fines_router.message(FineStates.wait_points_dec_value)
async def points_dec_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    try:
        delta = parse_amount(message.text)
    except ValueError as e:
        await message.answer(str(e))
        return

    user_id = (await state.get_data()).get("target_user_id")
    await state.clear()
    await decrease_user_points(user_id, delta)
    user = await get_user_by_id(user_id)
    await send_admin_card(message, user, f"✅ Очки уменьшены на {fmt_points(delta)}.\n\n")


# ---------- Admin: add fine (описание → стоимость) ----------

@fines_router.message(FineStates.wait_fine_text)
async def fine_text_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Описание штрафа не может быть пустым.")
        return
    await state.update_data(fine_text=text)
    await state.set_state(FineStates.wait_fine_cost)
    await message.answer("Стоимость штрафа в кадрах (0 — без оплаты, снимает только админ):")


@fines_router.message(FineStates.wait_fine_cost)
async def fine_cost_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    try:
        cost = parse_amount(message.text)
    except ValueError as e:
        await message.answer(str(e))
        return

    data = await state.get_data()
    await state.clear()
    fine = await add_fine(data.get("target_user_id"), data.get("fine_text"), cost)
    if not fine:
        await message.answer("❌ Не удалось добавить штраф.")
        return
    user = await get_user_by_id(fine.user_id)
    await send_admin_card(message, user, "✅ Штраф добавлен.\n\n")
```

- [ ] **Step 2: Удалить `handlers/admin.py`**

```bash
git rm handlers/admin.py
```

- [ ] **Step 3: Подключить роутер** — в `handlers/__init__.py`:
  - `from .admin import admin` → `from .fines import fines_router`
  - `admin_router.include_router(admin)` → `admin_router.include_router(fines_router)`

- [ ] **Step 4: Проверить**

Run: `venv_new/Scripts/python.exe -c "import handlers" && venv_new/Scripts/python.exe -m pytest tests -q && grep -rn "handlers.admin\b\|from .admin import" handlers app.py`
Expected: импорт OK, тесты PASS, grep ничего не находит.

- [ ] **Step 5: Commit**

```bash
git add handlers/fines.py handlers/__init__.py
git commit -m "feat: move match fines to fines table with cost and removal history

Removes handlers/admin.py: its event-creation half was attached to a
shadowed Router and never registered.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Блокировка пользователей

**Files:**
- Create: `middlewares/__init__.py`, `middlewares/ban.py`
- Modify: `handlers/fines.py`, `database/requests.py`, `app.py`
- Test: `tests/test_requests_users.py` (дописать)

**Interfaces:**
- Consumes: `handlers.fines` из Task 7
- Produces: `database.requests.set_banned(user_id: int, banned: bool) -> bool`, `database.requests.get_admin_tg_ids() -> list[int]`, `middlewares.BanMiddleware`, `middlewares.ban.BAN_TEXT`

- [ ] **Step 1: Падающие тесты** — дописать в `tests/test_requests_users.py`:

```python
def test_set_banned(make_user):
    uid = make_user(tg_id=300)
    assert asyncio.run(r.set_banned(uid, True)) is True
    assert asyncio.run(r.get_user(300)).is_banned is True
    asyncio.run(r.set_banned(uid, False))
    assert asyncio.run(r.get_user(300)).is_banned is False
    assert asyncio.run(r.set_banned(9999, True)) is False


def test_get_admin_tg_ids(make_user):
    make_user(name="adm", tg_id=1, status="admin")
    make_user(name="usr", tg_id=2)
    assert asyncio.run(r.get_admin_tg_ids()) == [1]
```

Run: `venv_new/Scripts/python.exe -m pytest tests/test_requests_users.py -v` → FAIL (`no attribute 'set_banned'`).

- [ ] **Step 2: Запросы** — в `database/requests.py` после `get_user_by_id`:

```python
async def set_banned(user_id: int, banned: bool) -> bool:
    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            return False
        user.is_banned = banned
        await session.commit()
        return True


async def get_admin_tg_ids() -> list:
    async with async_session() as session:
        result = await session.scalars(select(User.tg_id).where(User.status == "admin"))
        return list(result.all())
```

Run: `venv_new/Scripts/python.exe -m pytest tests -v` → PASS.

- [ ] **Step 3: Middleware** — `middlewares/ban.py`:

```python
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
```

`middlewares/__init__.py`:
```python
from .ban import BanMiddleware

__all__ = ["BanMiddleware"]
```

- [ ] **Step 4: Регистрация** — в `app.py`:
  - импорт: `from middlewares import BanMiddleware`
  - в `main()` сразу после `dp = Dispatcher()`:

```python
    dp.message.outer_middleware(BanMiddleware())
    dp.callback_query.outer_middleware(BanMiddleware())
```

- [ ] **Step 5: Кнопки и сценарий в `handlers/fines.py`**

Импорты — добавить:
```python
from aiogram.exceptions import TelegramAPIError
```
и `set_banned` в импорт из `database.requests`.

Комментарий в `FineAdminCb.action` дополнить `| ban | unban`. После `FineRemoveCb` добавить:
```python
class BanMsgCb(CallbackData, prefix="ban_msg"):
    user_id: int
    ban: bool
    with_msg: bool
```

В `FineStates` добавить `wait_ban_message = State()`.

В `kb_admin_user_actions` перед кнопкой «Назад»:
```python
    if user.is_banned:
        kb.button(text="Разблокировать", callback_data=FineAdminCb(action="unban", user_id=user.id).pack())
    else:
        kb.button(text="Заблокировать 🚫", callback_data=FineAdminCb(action="ban", user_id=user.id).pack())
```

В `admin_buttons` перед финальным `await callback.answer("Неизвестное действие."...)`:
```python
    if action in ("ban", "unban"):
        ban = action == "ban"
        if ban and user.status == "admin":
            await callback.answer("Нельзя заблокировать администратора.", show_alert=True)
            return
        kb = InlineKeyboardBuilder()
        kb.button(text="Да", callback_data=BanMsgCb(user_id=user.id, ban=ban, with_msg=True).pack())
        kb.button(text="Нет", callback_data=BanMsgCb(user_id=user.id, ban=ban, with_msg=False).pack())
        kb.adjust(2)
        await callback.message.answer("Хотите ли вы оставить сообщение пользователю?", reply_markup=kb.as_markup())
        await callback.answer()
        return
```

В конец файла:
```python
# ---------- Admin: ban / unban ----------

async def apply_ban(admin_message: Message, user_id: int, ban: bool, text: str = None):
    user = await get_user_by_id(user_id)
    if not user:
        await admin_message.answer("Игрок не найден.")
        return

    await set_banned(user.id, ban)
    report = f"✅ {user.name} {'заблокирован' if ban else 'разблокирован'}."
    if text is None:
        report += " Без уведомления."
    else:
        header = "🚫 Вы заблокированы." if ban else "✅ Вы разблокированы."
        try:
            await admin_message.bot.send_message(user.tg_id, f"{header}\n\n{text}")
        except TelegramAPIError:
            report += "\n⚠️ Уведомление не доставлено (пользователь остановил бота)."

    user = await get_user_by_id(user.id)
    await send_admin_card(admin_message, user, report + "\n\n")


@fines_router.callback_query(BanMsgCb.filter())
async def ban_message_choice(callback: CallbackQuery, callback_data: BanMsgCb, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступно только администратору.", show_alert=True)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    if callback_data.with_msg:
        await state.set_state(FineStates.wait_ban_message)
        await state.update_data(target_user_id=callback_data.user_id, ban=callback_data.ban)
        await callback.message.answer("Введите сообщение")
        return
    await apply_ban(callback.message, callback_data.user_id, callback_data.ban)


@fines_router.message(FineStates.wait_ban_message)
async def ban_message_apply(message: Message, state: FSMContext):
    if await deny_non_admin(message, state):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Сообщение не может быть пустым. Введите текст:")
        return
    data = await state.get_data()
    await state.clear()
    await apply_ban(message, data["target_user_id"], data["ban"], text)
```

- [ ] **Step 6: Проверить**

Run: `venv_new/Scripts/python.exe -c "import app" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: импорт OK (бот не стартует — `main()` под `__main__`), тесты PASS.

- [ ] **Step 7: Commit**

```bash
git add middlewares/__init__.py middlewares/ban.py handlers/fines.py database/requests.py app.py tests/test_requests_users.py
git commit -m "feat: block and unblock users from match fines with optional message

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Оплата штрафов (кадры и Telegram Stars)

**Files:**
- Create: `handlers/fine_payment.py`
- Modify: `handlers/__init__.py`

**Interfaces:**
- Consumes: `database.fines.get_active_fines/get_fine/pay_fine_with_cadrs/mark_fine_paid_stars`, `database.requests.get_user/get_admin_tg_ids`, `utils.fine_stars/fine_payload/parse_fine_payload/fmt_points`
- Produces: `fine_payment_router`, `FinePayCb(action: str, fine_id: int = 0)` — `action="list"` открывает список штрафов к оплате (используется кабинетом в Task 11)

- [ ] **Step 1: Создать `handlers/fine_payment.py`**

```python
"""Оплата матч-штрафов: кадрами или Telegram Stars (1 кадр = 5 ⭐)."""
from aiogram import Router, F
from aiogram.exceptions import TelegramAPIError
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.fines import get_active_fines, get_fine, mark_fine_paid_stars, pay_fine_with_cadrs
from database.requests import get_admin_tg_ids, get_user
from utils import fine_payload, fine_stars, fmt_points, parse_fine_payload

fine_payment_router = Router()

STARS_CURRENCY = "XTR"
CLOSED_TEXT = "Штраф уже закрыт."

CADRS_RESULT_TEXT = {
    "no_points": "Недостаточно кадров.",
    "not_active": CLOSED_TEXT,
    "free": "Этот штраф снимает только администратор.",
    "not_found": "Штраф не найден.",
}


class FinePayCb(CallbackData, prefix="fpay"):
    action: str  # list | choose | cadrs | stars
    fine_id: int = 0


async def load_payable(callback: CallbackQuery, fine_id: int):
    """(user, fine) для активного платного штрафа этого пользователя, иначе alert и None."""
    user = await get_user(callback.from_user.id)
    fine = await get_fine(fine_id)
    if not user or not fine or fine.user_id != user.id or fine.status != "active" or not fine.cost:
        await callback.answer(CLOSED_TEXT, show_alert=True)
        return None
    return user, fine


@fine_payment_router.callback_query(FinePayCb.filter(F.action == "list"))
async def pay_list(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    fines = [f for f in await get_active_fines(user.id) if f.cost] if user else []
    if not fines:
        await callback.answer("Нет штрафов для оплаты.", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for i, fine in enumerate(fines, start=1):
        kb.button(
            text=f"{i}. {fine.description[:40]} — {fmt_points(fine.cost)} кадров",
            callback_data=FinePayCb(action="choose", fine_id=fine.id).pack(),
        )
    kb.adjust(1)
    await callback.message.answer("Выбери штраф для оплаты:", reply_markup=kb.as_markup())
    await callback.answer()


@fine_payment_router.callback_query(FinePayCb.filter(F.action == "choose"))
async def pay_choose(callback: CallbackQuery, callback_data: FinePayCb):
    loaded = await load_payable(callback, callback_data.fine_id)
    if not loaded:
        return
    user, fine = loaded
    stars = fine_stars(fine.cost)

    kb = InlineKeyboardBuilder()
    kb.button(text=f"🎞 Кадрами — {fmt_points(fine.cost)}", callback_data=FinePayCb(action="cadrs", fine_id=fine.id).pack())
    kb.button(text=f"⭐ Звёздами — {stars}", callback_data=FinePayCb(action="stars", fine_id=fine.id).pack())
    kb.adjust(1)
    await callback.message.answer(
        f"Штраф: {fine.description}\n"
        f"Стоимость: {fmt_points(fine.cost)} кадров или {stars} ⭐\n"
        f"На счёте: {fmt_points(user.points)} кадров",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@fine_payment_router.callback_query(FinePayCb.filter(F.action == "cadrs"))
async def pay_cadrs(callback: CallbackQuery, callback_data: FinePayCb):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь с помощью /start", show_alert=True)
        return
    fine = await get_fine(callback_data.fine_id)
    result = await pay_fine_with_cadrs(callback_data.fine_id, user.id)
    if result != "ok":
        await callback.answer(CADRS_RESULT_TEXT[result], show_alert=True)
        return
    await callback.message.edit_text(f"✅ Штраф оплачен. Списано {fmt_points(fine.cost)} кадров.")
    await callback.answer()


@fine_payment_router.callback_query(FinePayCb.filter(F.action == "stars"))
async def pay_stars(callback: CallbackQuery, callback_data: FinePayCb):
    loaded = await load_payable(callback, callback_data.fine_id)
    if not loaded:
        return
    user, fine = loaded
    await callback.message.answer_invoice(
        title="Оплата матч-штрафа",
        description=fine.description[:255],
        payload=fine_payload(fine.id, user.id),
        currency=STARS_CURRENCY,
        prices=[LabeledPrice(label="Матч-штраф", amount=fine_stars(fine.cost))],
    )
    await callback.answer()


@fine_payment_router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    parsed = parse_fine_payload(query.invoice_payload)
    user = await get_user(query.from_user.id)
    fine = await get_fine(parsed[0]) if parsed else None
    ok = bool(
        parsed and user and fine
        and fine.user_id == user.id == parsed[1]
        and fine.status == "active" and fine.cost
        and query.currency == STARS_CURRENCY
        and query.total_amount == fine_stars(fine.cost)
    )
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Штраф уже закрыт или изменился. Открой личный кабинет заново.")


@fine_payment_router.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    parsed = parse_fine_payload(payment.invoice_payload)
    fine_id = parsed[0] if parsed else 0
    if parsed and await mark_fine_paid_stars(fine_id, payment.total_amount, payment.telegram_payment_charge_id):
        await message.answer(f"✅ Штраф оплачен: {payment.total_amount} ⭐. Спасибо!")
        return

    # Штраф закрыли между pre_checkout и оплатой — звёзды нужно вернуть вручную
    await message.answer("⚠️ Оплата получена, но штраф уже был закрыт. Администратор вернёт звёзды.")
    note = (
        f"⚠️ Оплата за закрытый штраф #{fine_id}\n"
        f"Пользователь tg_id: {message.from_user.id}\n"
        f"Звёзд: {payment.total_amount}\n"
        f"charge_id: {payment.telegram_payment_charge_id}"
    )
    for tg_id in await get_admin_tg_ids():
        try:
            await message.bot.send_message(tg_id, note)
        except TelegramAPIError:
            pass
```

- [ ] **Step 2: Подключить** — в `handlers/__init__.py`:
  - импорт `from .fine_payment import fine_payment_router`
  - после `user_router.include_router(user)` добавить `user_router.include_router(fine_payment_router)`

- [ ] **Step 3: Проверить**

Run: `venv_new/Scripts/python.exe -c "import app" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: OK, PASS.

- [ ] **Step 4: Commit**

```bash
git add handlers/fine_payment.py handlers/__init__.py
git commit -m "feat: pay match fines with cadrs or Telegram Stars

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Этап 3 — статус наград, личный кабинет, меню

### Task 10: Статус выдачи наград

**Files:**
- Modify: `database/requests.py`, `handlers/fines.py`
- Test: `tests/test_requests_users.py` (дописать)

**Interfaces:**
- Produces:
  - `database.requests.get_user_rewards_with_status(user_id: int) -> list[tuple[UserReward, Reward]]` (новые сверху)
  - `database.requests.toggle_reward_issued(user_reward_id: int) -> tuple[bool, int | None, str] | None` — `(новый issued, tg_id владельца, название награды)`

- [ ] **Step 1: Падающий тест** — дописать в `tests/test_requests_users.py`:

```python
from database.models import Reward, UserReward


def add_reward_to(db, user_id, name="Камуфляж №1") -> int:
    async def go():
        async with db() as session:
            reward = Reward(name=name, gift_link="https://x", price=1)
            session.add(reward)
            await session.flush()
            ur = UserReward(user_id=user_id, reward_id=reward.id)
            session.add(ur)
            await session.commit()
            return ur.id
    return asyncio.run(go())


def test_reward_status_toggle(db, make_user):
    uid = make_user(tg_id=400)
    ur_id = add_reward_to(db, uid)

    [(ur, reward)] = asyncio.run(r.get_user_rewards_with_status(uid))
    assert (ur.id, reward.name, ur.issued) == (ur_id, "Камуфляж №1", False)

    assert asyncio.run(r.toggle_reward_issued(ur_id)) == (True, 400, "Камуфляж №1")
    assert asyncio.run(r.toggle_reward_issued(ur_id)) == (False, 400, "Камуфляж №1")
    assert asyncio.run(r.toggle_reward_issued(9999)) is None
```

Run: `venv_new/Scripts/python.exe -m pytest tests/test_requests_users.py -v` → FAIL.

- [ ] **Step 2: Запросы** — в `database/requests.py` после `get_user_rewards`:

```python
async def get_user_rewards_with_status(user_id: int) -> list:
    """[(UserReward, Reward), ...] — покупки пользователя со статусом выдачи."""
    async with async_session() as session:
        result = await session.execute(
            select(UserReward, Reward)
            .join(Reward, Reward.id == UserReward.reward_id)
            .where(UserReward.user_id == user_id)
            .order_by(UserReward.created_at.desc(), UserReward.id.desc())
        )
        return [(ur, reward) for ur, reward in result.all()]


async def toggle_reward_issued(user_reward_id: int):
    """Переключает «выдан/не выдан». Возвращает (issued, tg_id владельца, название) или None."""
    async with async_session() as session:
        ur = await session.get(UserReward, user_reward_id)
        if not ur:
            return None
        ur.issued = not ur.issued
        issued = ur.issued
        reward = await session.get(Reward, ur.reward_id)
        owner = await session.get(User, ur.user_id)
        await session.commit()
        return issued, (owner.tg_id if owner else None), (reward.name if reward else "Награда")
```

Run: `venv_new/Scripts/python.exe -m pytest tests -v` → PASS.

- [ ] **Step 3: Админский список наград в `handlers/fines.py`**

Импорты: добавить `get_user_rewards_with_status, toggle_reward_issued` в импорт из `database.requests`.

Комментарий `FineAdminCb.action` дополнить `| rewards_list`. После `BanMsgCb` добавить:
```python
class RewardToggleCb(CallbackData, prefix="rw_tgl"):
    user_reward_id: int
    user_id: int
```

В `kb_admin_user_actions` в кортеж кнопок после `("Штрафы игрока", "fines_list"),` добавить `("Награды игрока", "rewards_list"),`.

Рядом с `render_fines_list` добавить:
```python
def render_rewards_list(user, items) -> str:
    if not items:
        return f"У игрока {user.name} нет покупок."
    lines = [f"Награды {user.name} (нажми, чтобы переключить):"]
    lines += [f"{i}. {reward.name} — {'выдан ✅' if ur.issued else 'не выдан ❌'}"
              for i, (ur, reward) in enumerate(items, start=1)]
    return "\n".join(lines)


def kb_rewards_list(user_id: int, items):
    kb = InlineKeyboardBuilder()
    for i, (ur, _reward) in enumerate(items, start=1):
        kb.button(text=f"{'✅' if ur.issued else '❌'} №{i}",
                  callback_data=RewardToggleCb(user_reward_id=ur.id, user_id=user_id).pack())
    kb.button(text="◀️ К игроку", callback_data=FineAdminCb(action="card", user_id=user_id).pack())
    kb.adjust(4)
    return kb.as_markup()
```

В `admin_buttons` перед веткой `ban/unban`:
```python
    if action == "rewards_list":
        items = await get_user_rewards_with_status(user.id)
        await callback.message.answer(render_rewards_list(user, items), reply_markup=kb_rewards_list(user.id, items))
        await callback.answer()
        return
```

В конец файла:
```python
# ---------- Admin: reward issued toggle ----------

@fines_router.callback_query(RewardToggleCb.filter())
async def reward_toggle(callback: CallbackQuery, callback_data: RewardToggleCb):
    if not await is_admin(callback.from_user.id):
        await callback.answer("Доступно только администратору.", show_alert=True)
        return

    toggled = await toggle_reward_issued(callback_data.user_reward_id)
    if toggled is None:
        await callback.answer("Покупка не найдена.", show_alert=True)
        return

    issued, owner_tg_id, reward_name = toggled
    await callback.answer("Выдан ✅" if issued else "Не выдан ❌")
    if issued and owner_tg_id:
        try:
            await callback.bot.send_message(owner_tg_id, f"🎁 Награда «{reward_name}» выдана ✅")
        except TelegramAPIError:
            pass

    user = await get_user_by_id(callback_data.user_id)
    if user:
        items = await get_user_rewards_with_status(user.id)
        await callback.message.edit_text(render_rewards_list(user, items), reply_markup=kb_rewards_list(user.id, items))
```

- [ ] **Step 4: Проверить**

Run: `venv_new/Scripts/python.exe -c "import app" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: OK, PASS.

- [ ] **Step 5: Commit**

```bash
git add database/requests.py handlers/fines.py tests/test_requests_users.py
git commit -m "feat: admins can mark purchased rewards as issued

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Личный кабинет и новое меню

**Files:**
- Create: `handlers/cabinet.py`, `database/training.py`, `tests/test_cabinet.py`
- Modify: `utils.py`, `keyboards/userkeyboard.py`, `keyboards/adminkeyboard.py`, `handlers/__init__.py`

**Interfaces:**
- Consumes: `get_user_rewards_with_status` (Task 10), `get_active_fines` (Task 6), `FinePayCb` (Task 9), `handlers.start.Name`
- Produces:
  - `utils.render_cabinet(name, points, rewards: list[tuple[str, bool]], tests: list[tuple[str, bool]], fines: list[tuple[str, float]]) -> str`
  - `database.training.get_test_statuses(user_id: int) -> list[tuple[int, str, bool]]` — `(test_id, title, passed)` по `id`
  - `keyboards.userkeyboard.user_rows(with_training: bool) -> list[list[KeyboardButton]]` — используется админской клавиатурой
  - `handlers.cabinet.cabinet_router`, `CABINET_BUTTON = "Личный кабинет"`

- [ ] **Step 1: Падающие тесты** — `tests/test_cabinet.py`:

```python
import asyncio

from database import training as t
from database.models import TrainingAttempt, TrainingTest
from utils import render_cabinet


def test_render_cabinet_full():
    text = render_cabinet(
        "Youra", 42,
        rewards=[("Камуфляж №1", True), ("Камуфляж №2", False)],
        tests=[("Тест А", True), ("Тест Б", False)],
        fines=[("Оскорбление", 3), ("Старый штраф", 0)],
    )
    assert "👤 Ник: Youra" in text
    assert "🎞 Кадры: 42" in text
    assert " • Камуфляж №1 — выдан ✅" in text
    assert " • Камуфляж №2 — не выдан ❌" in text
    assert " • Тест А — пройден 🟢" in text
    assert " • Тест Б — не пройден 🔴" in text
    assert " 1. Оскорбление — 3 кадров" in text
    assert " 2. Старый штраф" in text and "Старый штраф —" not in text


def test_render_cabinet_empty():
    text = render_cabinet("Youra", 0, rewards=[], tests=[], fines=[])
    assert "🎁 Награды: нет" in text
    assert "📚 Тесты: нет тестов" in text
    assert "⚠️ Штрафы: нет" in text


def test_get_test_statuses(db, make_user):
    uid = make_user()

    async def seed():
        async with db() as session:
            a, b = TrainingTest(title="А", cost=0), TrainingTest(title="Б", cost=0)
            session.add_all([a, b])
            await session.flush()
            session.add_all([
                TrainingAttempt(user_id=uid, test_id=a.id, correct_count=1, total=5, passed=False),
                TrainingAttempt(user_id=uid, test_id=a.id, correct_count=5, total=5, passed=True),
                TrainingAttempt(user_id=uid, test_id=b.id, correct_count=0, total=5, passed=False),
            ])
            await session.commit()
            return a.id, b.id

    a_id, b_id = asyncio.run(seed())
    assert asyncio.run(t.get_test_statuses(uid)) == [(a_id, "А", True), (b_id, "Б", False)]
```

Run: `venv_new/Scripts/python.exe -m pytest tests/test_cabinet.py -v` → FAIL (`cannot import name 'training'`).

- [ ] **Step 2: `render_cabinet`** — дописать в `utils.py`:

```python
# ── Личный кабинет ───────────────────────────────────────────────────────────

def render_cabinet(name, points, rewards, tests, fines) -> str:
    """rewards/tests — [(название, выдан/пройден)], fines — [(описание, стоимость)]."""
    emoji, _ = cadr_tier(points)
    lines = [f"👤 Ник: {name}", f"🎞 Кадры: {fmt_points(points)} {emoji}".rstrip(), ""]

    if rewards:
        lines.append("🎁 Награды:")
        lines += [f" • {title} — {'выдан ✅' if ok else 'не выдан ❌'}" for title, ok in rewards]
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
        lines += [f" {i}. {desc}" + (f" — {fmt_points(cost)} кадров" if cost else "")
                  for i, (desc, cost) in enumerate(fines, start=1)]
    else:
        lines.append("⚠️ Штрафы: нет")
    return "\n".join(lines)
```

- [ ] **Step 3: `database/training.py`** (остальные функции добавит Task 12):

```python
"""Обучение: тесты, вопросы, попытки."""
from sqlalchemy import delete, func, select, update

from database.models import TrainingAttempt, TrainingQuestion, TrainingTest, User, async_session

MAX_QUESTIONS = 25


async def get_test_statuses(user_id: int) -> list:
    """[(test_id, title, passed)] по всем тестам."""
    async with async_session() as session:
        tests = (await session.execute(
            select(TrainingTest.id, TrainingTest.title).order_by(TrainingTest.id)
        )).all()
        passed = set((await session.scalars(
            select(TrainingAttempt.test_id)
            .where(TrainingAttempt.user_id == user_id, TrainingAttempt.passed.is_(True))
        )).all())
    return [(test_id, title, test_id in passed) for test_id, title in tests]
```

Run: `venv_new/Scripts/python.exe -m pytest tests -v` → PASS.

- [ ] **Step 4: `handlers/cabinet.py`**

```python
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
```

- [ ] **Step 5: Клавиатуры**

`keyboards/userkeyboard.py` — заменить целиком:
```python
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def user_rows(with_training: bool = False) -> list:
    """Основные кнопки пользователя (3×3). Кнопка «Обучение» появится вместе с разделом."""
    middle = [KeyboardButton(text='Матч-штрафы')]
    if with_training:
        middle.append(KeyboardButton(text='Обучение'))
    middle.append(KeyboardButton(text='Награды'))
    return [
        [KeyboardButton(text='Личный кабинет'), KeyboardButton(text='Правила'), KeyboardButton(text='🔍 Поиск')],
        middle,
        [KeyboardButton(text='Список танков'), KeyboardButton(text='Список сражений'), KeyboardButton(text='Список ивентов')],
    ]


userboard = ReplyKeyboardMarkup(keyboard=user_rows(), resize_keyboard=True)
```

`keyboards/adminkeyboard.py` — заменить целиком:
```python
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from .userkeyboard import user_rows

ADMIN_ROWS = [
    [KeyboardButton(text='Добавить ивент'), KeyboardButton(text='Редактировать ивент'), KeyboardButton(text='Удалить ивент')],
    [KeyboardButton(text='Добавить награду'), KeyboardButton(text='Изменить награду'), KeyboardButton(text='Удалить награду')],
    [KeyboardButton(text='Добавить танк'), KeyboardButton(text='Изменить танк'), KeyboardButton(text='Удалить танк')],
    [KeyboardButton(text='Добавить сражение'), KeyboardButton(text='Изменить сражение'), KeyboardButton(text='Удалить сражение')],
]

adminboard = ReplyKeyboardMarkup(keyboard=user_rows() + ADMIN_ROWS, resize_keyboard=True)
```

- [ ] **Step 6: Подключить роутер** — в `handlers/__init__.py`: импорт `from .cabinet import cabinet_router`; `user_router.include_router(cabinet_router)` сразу после `fine_payment_router`.

- [ ] **Step 7: Проверить**

Run: `venv_new/Scripts/python.exe -c "import app" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: OK, PASS. Проверить, что кнопки «Правила», «Награды», «Список танков», «Список сражений», «Список ивентов», «🔍 Поиск», «Матч-штрафы» имеют обработчики:
`grep -n "'Правила'\|\"Награды\"\|'Список танков'\|\"Список сражений\"\|\"Список ивентов\"\|SEARCH_BUTTON\|FINES_BUTTONS\|CABINET_BUTTON" handlers/*.py`

- [ ] **Step 8: Commit**

```bash
git add handlers/cabinet.py database/training.py utils.py keyboards/userkeyboard.py keyboards/adminkeyboard.py handlers/__init__.py tests/test_cabinet.py
git commit -m "feat: personal cabinet with rewards, tests, fines and new main menu

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Этап 4 — обучение

### Task 12: Запросы для тестов

**Files:**
- Modify: `database/training.py`
- Create: `tests/test_training_db.py`

**Interfaces:**
- Produces (`database/training.py`), вопрос как dict: `{"text": str, "options": [str, str, str, str], "correct": int 1..4}`:
  - `question_to_dict(q: TrainingQuestion) -> dict`
  - `create_test(title: str, cost: float, questions: list[dict]) -> int` (ValueError при 0 или > 25 вопросах)
  - `get_tests_with_counts() -> list[tuple[TrainingTest, int]]`
  - `get_test(test_id) -> TrainingTest | None`, `get_questions(test_id) -> list[TrainingQuestion]` (по `position`), `get_question(question_id) -> TrainingQuestion | None`
  - `update_test(test_id, **fields) -> bool`, `update_question(question_id, q: dict) -> bool`
  - `add_question(test_id, q: dict) -> bool` (False при 25), `delete_question(question_id) -> bool` (False для последнего)
  - `delete_test(test_id) -> bool` (удаляет вопросы и попытки)
  - `has_passed(user_id, test_id) -> bool`, `last_failed_at(user_id, test_id) -> datetime | None`
  - `charge_points(user_id, cost) -> bool` (атомарно; cost 0 → True)
  - `record_attempt(user_id, test_id, correct, total, passed) -> bool` (False, если тест удалён)

- [ ] **Step 1: Падающие тесты** — `tests/test_training_db.py`:

```python
import asyncio

import pytest

from database import training as t
from database.requests import get_user_by_id


def run(coro):
    return asyncio.run(coro)


def q(n: int, correct: int = 1) -> dict:
    return {"text": f"Вопрос {n}", "options": ["a", "b", "c", "d"], "correct": correct}


def test_create_and_read(db):
    test_id = run(t.create_test("Тест А", 2.5, [q(1, 2), q(2, 4)]))
    [(test, count)] = run(t.get_tests_with_counts())
    assert (test.id, test.title, test.cost, count) == (test_id, "Тест А", 2.5, 2)
    questions = run(t.get_questions(test_id))
    assert [t.question_to_dict(x) for x in questions] == [q(1, 2), q(2, 4)]


def test_create_validates_count(db):
    with pytest.raises(ValueError):
        run(t.create_test("x", 0, []))
    with pytest.raises(ValueError):
        run(t.create_test("x", 0, [q(i) for i in range(26)]))


def test_edit_questions(db):
    test_id = run(t.create_test("x", 0, [q(1)]))
    [first] = run(t.get_questions(test_id))

    assert run(t.delete_question(first.id)) is False  # последний вопрос не удаляется
    assert run(t.add_question(test_id, q(2, 3))) is True
    assert run(t.update_question(first.id, q(9, 4))) is True
    assert [t.question_to_dict(x) for x in run(t.get_questions(test_id))] == [q(9, 4), q(2, 3)]
    assert run(t.delete_question(first.id)) is True
    assert len(run(t.get_questions(test_id))) == 1
    assert run(t.update_test(test_id, title="Новое", cost=1)) is True
    assert (run(t.get_test(test_id)).title, run(t.get_test(test_id)).cost) == ("Новое", 1)
    assert run(t.update_test(999, title="x")) is False


def test_add_question_limit(db):
    test_id = run(t.create_test("x", 0, [q(i) for i in range(25)]))
    assert run(t.add_question(test_id, q(26))) is False


def test_attempts_and_delete(db, make_user):
    uid = make_user()
    test_id = run(t.create_test("x", 0, [q(1)]))
    assert run(t.has_passed(uid, test_id)) is False
    assert run(t.last_failed_at(uid, test_id)) is None

    assert run(t.record_attempt(uid, test_id, 0, 1, False)) is True
    assert run(t.last_failed_at(uid, test_id)) is not None
    assert run(t.record_attempt(uid, test_id, 1, 1, True)) is True
    assert run(t.has_passed(uid, test_id)) is True

    assert run(t.delete_test(test_id)) is True
    assert run(t.get_test(test_id)) is None
    assert run(t.get_questions(test_id)) == []
    assert run(t.get_test_statuses(uid)) == []
    assert run(t.record_attempt(uid, test_id, 1, 1, True)) is False
    assert run(t.delete_test(test_id)) is False


def test_charge_points(make_user):
    uid = make_user(points=5)
    assert run(t.charge_points(uid, 0)) is True
    assert run(t.charge_points(uid, 6)) is False
    assert run(t.charge_points(uid, 2.5)) is True
    assert run(get_user_by_id(uid)).points == 2.5
```

Run: `venv_new/Scripts/python.exe -m pytest tests/test_training_db.py -v` → FAIL (`no attribute 'create_test'`).

- [ ] **Step 2: Реализовать** — дописать в `database/training.py`:

```python
def question_to_dict(q) -> dict:
    return {"text": q.text, "options": [q.option_1, q.option_2, q.option_3, q.option_4], "correct": q.correct}


def _question_columns(q: dict) -> dict:
    o = q["options"]
    return {"text": q["text"], "option_1": o[0], "option_2": o[1], "option_3": o[2],
            "option_4": o[3], "correct": int(q["correct"])}


async def create_test(title: str, cost: float, questions: list) -> int:
    if not 1 <= len(questions) <= MAX_QUESTIONS:
        raise ValueError(f"В тесте должно быть от 1 до {MAX_QUESTIONS} вопросов")
    async with async_session() as session:
        test = TrainingTest(title=title, cost=round(float(cost), 2))
        session.add(test)
        await session.flush()
        for position, q in enumerate(questions, start=1):
            session.add(TrainingQuestion(test_id=test.id, position=position, **_question_columns(q)))
        await session.commit()
        return test.id


async def get_tests_with_counts() -> list:
    async with async_session() as session:
        rows = await session.execute(
            select(TrainingTest, func.count(TrainingQuestion.id))
            .outerjoin(TrainingQuestion, TrainingQuestion.test_id == TrainingTest.id)
            .group_by(TrainingTest.id)
            .order_by(TrainingTest.id)
        )
        return [(test, count) for test, count in rows.all()]


async def get_test(test_id: int):
    async with async_session() as session:
        return await session.get(TrainingTest, test_id)


async def get_questions(test_id: int) -> list:
    async with async_session() as session:
        result = await session.scalars(
            select(TrainingQuestion)
            .where(TrainingQuestion.test_id == test_id)
            .order_by(TrainingQuestion.position, TrainingQuestion.id)
        )
        return list(result.all())


async def get_question(question_id: int):
    async with async_session() as session:
        return await session.get(TrainingQuestion, question_id)


async def update_test(test_id: int, **fields) -> bool:
    async with async_session() as session:
        test = await session.get(TrainingTest, test_id)
        if not test:
            return False
        for name, value in fields.items():
            setattr(test, name, value)
        await session.commit()
        return True


async def update_question(question_id: int, q: dict) -> bool:
    async with async_session() as session:
        question = await session.get(TrainingQuestion, question_id)
        if not question:
            return False
        for name, value in _question_columns(q).items():
            setattr(question, name, value)
        await session.commit()
        return True


async def _count_questions(session, test_id: int) -> int:
    return await session.scalar(
        select(func.count(TrainingQuestion.id)).where(TrainingQuestion.test_id == test_id)
    )


async def add_question(test_id: int, q: dict) -> bool:
    async with async_session() as session:
        if not await session.get(TrainingTest, test_id):
            return False
        if await _count_questions(session, test_id) >= MAX_QUESTIONS:
            return False
        last = await session.scalar(
            select(func.max(TrainingQuestion.position)).where(TrainingQuestion.test_id == test_id)
        )
        session.add(TrainingQuestion(test_id=test_id, position=(last or 0) + 1, **_question_columns(q)))
        await session.commit()
        return True


async def delete_question(question_id: int) -> bool:
    async with async_session() as session:
        question = await session.get(TrainingQuestion, question_id)
        if not question or await _count_questions(session, question.test_id) <= 1:
            return False
        await session.delete(question)
        await session.commit()
        return True


async def delete_test(test_id: int) -> bool:
    # SQLite без PRAGMA foreign_keys не выполняет ON DELETE CASCADE — удаляем явно
    async with async_session() as session:
        test = await session.get(TrainingTest, test_id)
        if not test:
            return False
        await session.execute(delete(TrainingAttempt).where(TrainingAttempt.test_id == test_id))
        await session.execute(delete(TrainingQuestion).where(TrainingQuestion.test_id == test_id))
        await session.delete(test)
        await session.commit()
        return True


async def has_passed(user_id: int, test_id: int) -> bool:
    async with async_session() as session:
        found = await session.scalar(
            select(TrainingAttempt.id)
            .where(TrainingAttempt.user_id == user_id, TrainingAttempt.test_id == test_id,
                   TrainingAttempt.passed.is_(True))
            .limit(1)
        )
        return found is not None


async def last_failed_at(user_id: int, test_id: int):
    async with async_session() as session:
        return await session.scalar(
            select(TrainingAttempt.created_at)
            .where(TrainingAttempt.user_id == user_id, TrainingAttempt.test_id == test_id,
                   TrainingAttempt.passed.is_(False))
            .order_by(TrainingAttempt.created_at.desc())
            .limit(1)
        )


async def charge_points(user_id: int, cost: float) -> bool:
    """Атомарно списывает кадры, если их хватает."""
    if not cost:
        return True
    async with async_session() as session:
        result = await session.execute(
            update(User)
            .where(User.id == user_id, User.points >= cost)
            .values(points=func.round(User.points - cost, 2))
        )
        await session.commit()
        return result.rowcount == 1


async def record_attempt(user_id: int, test_id: int, correct: int, total: int, passed: bool) -> bool:
    async with async_session() as session:
        if not await session.get(TrainingTest, test_id):
            return False
        session.add(TrainingAttempt(user_id=user_id, test_id=test_id,
                                    correct_count=correct, total=total, passed=passed))
        await session.commit()
        return True
```

- [ ] **Step 3: Запустить тесты**

Run: `venv_new/Scripts/python.exe -m pytest tests -v`
Expected: все PASS

- [ ] **Step 4: Commit**

```bash
git add database/training.py tests/test_training_db.py
git commit -m "feat: training tests storage, attempts and point charging

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Раздел «Обучение» для пользователя

**Files:**
- Create: `handlers/training.py`
- Modify: `handlers/__init__.py`

**Interfaces:**
- Consumes: всё из Task 12; `utils.start_decision/fmt_duration/is_quiz_passed/fmt_cost`
- Produces: `training_router`, `TRAINING_BUTTON = "Обучение"`

- [ ] **Step 1: Создать `handlers/training.py`**

```python
"""Раздел «Обучение»: список тестов и прохождение."""
from datetime import datetime

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import get_user
from database.training import (
    charge_points, get_questions, get_test, get_test_statuses, get_tests_with_counts,
    has_passed, last_failed_at, question_to_dict, record_attempt,
)
from utils import fmt_cost, fmt_duration, is_quiz_passed, start_decision

training_router = Router()

TRAINING_BUTTON = "Обучение"


class TrainCb(CallbackData, prefix="train"):
    action: str  # open | start
    test_id: int


class TrainAnswerCb(CallbackData, prefix="train_ans"):
    index: int
    option: int


class TrainStates(StatesGroup):
    in_test = State()


def question_text(data: dict) -> str:
    i = data["tt_i"]
    q = data["tt_q"][i]
    options = "\n".join(f"{n}. {opt}" for n, opt in enumerate(q["options"], start=1))
    return f"❓ Вопрос {i + 1}/{len(data['tt_q'])}\n\n{q['text']}\n\n{options}"


async def send_question(message: Message, data: dict):
    kb = InlineKeyboardBuilder()
    for n in range(1, 5):
        kb.button(text=str(n), callback_data=TrainAnswerCb(index=data["tt_i"], option=n).pack())
    kb.adjust(4)
    await message.answer(question_text(data), reply_markup=kb.as_markup())


@training_router.message(F.text == TRAINING_BUTTON)
@training_router.message(Command("training"))
async def training_list(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    if not user or not user.name:
        await message.answer("Сначала зарегистрируйтесь с помощью /start")
        return

    tests = await get_tests_with_counts()
    if not tests:
        await message.answer("📚 Тестов пока нет.")
        return

    passed = {test_id: ok for test_id, _, ok in await get_test_statuses(user.id)}
    lines = ["📚 Обучение", ""]
    kb = InlineKeyboardBuilder()
    for i, (test, count) in enumerate(tests, start=1):
        mark = "🟢" if passed.get(test.id) else "🔴"
        lines.append(f"{i}. {test.title} — {count} вопросов — {fmt_cost(test.cost)} {mark}")
        kb.button(text=f"{i}. {test.title}", callback_data=TrainCb(action="open", test_id=test.id).pack())
    kb.adjust(1)
    await message.answer("\n".join(lines), reply_markup=kb.as_markup())


@training_router.callback_query(TrainCb.filter(F.action == "open"))
async def training_open(callback: CallbackQuery, callback_data: TrainCb):
    test = await get_test(callback_data.test_id)
    if not test:
        await callback.answer("Тест не найден.", show_alert=True)
        return
    count = len(await get_questions(test.id))
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Начать", callback_data=TrainCb(action="start", test_id=test.id).pack())
    await callback.message.answer(
        f"📘 {test.title}\n\n"
        f"Вопросов: {count}\n"
        f"Стоимость попытки: {fmt_cost(test.cost)}\n"
        f"Для прохождения нужно 80% верных ответов.",
        reply_markup=kb.as_markup(),
    )
    await callback.answer()


@training_router.callback_query(TrainCb.filter(F.action == "start"))
async def training_start(callback: CallbackQuery, callback_data: TrainCb, state: FSMContext):
    user = await get_user(callback.from_user.id)
    test = await get_test(callback_data.test_id)
    questions = await get_questions(callback_data.test_id) if test else []
    if not user or not test or not questions:
        await callback.answer("Тест не найден.", show_alert=True)
        return

    decision, left = start_decision(
        await has_passed(user.id, test.id),
        await last_failed_at(user.id, test.id),
        user.points, test.cost, datetime.now(),
    )
    if decision == "passed":
        await callback.answer("✅ Тест уже пройден", show_alert=True)
        return
    if decision == "cooldown":
        await callback.answer(f"Попробуй через {fmt_duration(left)}", show_alert=True)
        return
    if decision == "no_points" or not await charge_points(user.id, test.cost):
        await callback.answer("Недостаточно кадров", show_alert=True)
        return

    await state.set_state(TrainStates.in_test)
    data = {
        "tt_id": test.id,
        "tt_title": test.title,
        "tt_q": [question_to_dict(q) for q in questions],
        "tt_i": 0,
        "tt_ok": 0,
    }
    await state.set_data(data)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await send_question(callback.message, data)


@training_router.callback_query(TrainAnswerCb.filter())
async def training_answer(callback: CallbackQuery, callback_data: TrainAnswerCb, state: FSMContext):
    if await state.get_state() != TrainStates.in_test.state:
        await callback.answer("Тест прерван. Начни заново через «Обучение».", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return

    data = await state.get_data()
    if callback_data.index != data["tt_i"]:
        await callback.answer()  # повторное нажатие на уже отвеченный вопрос
        return

    q = data["tt_q"][data["tt_i"]]
    data["tt_ok"] += int(callback_data.option == q["correct"])
    data["tt_i"] += 1
    await state.update_data(tt_i=data["tt_i"], tt_ok=data["tt_ok"])
    await callback.message.edit_text(f"{callback.message.text}\n\nТвой ответ: {callback_data.option}")
    await callback.answer()

    total = len(data["tt_q"])
    if data["tt_i"] < total:
        await send_question(callback.message, data)
        return

    await state.clear()
    correct = data["tt_ok"]
    passed = is_quiz_passed(correct, total)
    user = await get_user(callback.from_user.id)
    if user:
        await record_attempt(user.id, data["tt_id"], correct, total, passed)
    if passed:
        await callback.message.answer(f"✅ Тест «{data['tt_title']}» пройден! {correct} из {total} верно.")
    else:
        await callback.message.answer(f"{total - correct} ошибок из {total}. Попробуй ещё раз через 24 ч.")
```

- [ ] **Step 2: Подключить** — в `handlers/__init__.py`: импорт `from .training import training_router`; `user_router.include_router(training_router)` после `cabinet_router`.

- [ ] **Step 3: Проверить**

Run: `venv_new/Scripts/python.exe -c "import app" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: OK, PASS.

- [ ] **Step 4: Commit**

```bash
git add handlers/training.py handlers/__init__.py
git commit -m "feat: training section with paid attempts and 24h cooldown

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Конструктор тестов для админа и кнопки в меню

**Files:**
- Create: `handlers/admin_training.py`
- Modify: `handlers/__init__.py`, `keyboards/userkeyboard.py`, `keyboards/adminkeyboard.py`

**Interfaces:**
- Consumes: всё из Task 12; `utils.parse_amount/parse_options/fmt_cost`
- Produces: `admin_training`, `TESTS_ADMIN_BUTTON = "Тесты ⚙️"`

- [ ] **Step 1: Создать `handlers/admin_training.py`**

```python
"""Конструктор тестов: создание, изменение, удаление (только админ)."""
from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import is_admin
from database.training import (
    MAX_QUESTIONS, add_question, create_test, delete_question, delete_test, get_question,
    get_questions, get_test, get_tests_with_counts, update_question, update_test,
)
from utils import fmt_cost, parse_amount, parse_options

admin_training = Router()

TESTS_ADMIN_BUTTON = "Тесты ⚙️"


class ATestCb(CallbackData, prefix="atest"):
    # create | edit_list | delete_list | edit | delete | delete_yes | cancel
    # | title | cost | questions | add_q | del_q_list
    action: str
    test_id: int = 0


class AQuestionCb(CallbackData, prefix="aq"):
    action: str  # edit | delete
    question_id: int
    test_id: int


class ACorrectCb(CallbackData, prefix="acorr"):
    option: int


class ATestStates(StatesGroup):
    title = State()
    cost = State()
    count = State()
    q_text = State()
    q_options = State()
    q_correct = State()
    new_title = State()
    new_cost = State()


async def admin_only(event, state: FSMContext = None) -> bool:
    """True — можно продолжать; иначе сообщает об отказе и сбрасывает состояние."""
    if await is_admin(event.from_user.id):
        return True
    if state:
        await state.clear()
    if isinstance(event, CallbackQuery):
        await event.answer("Доступно только администратору.", show_alert=True)
    else:
        await event.answer("Доступно только администратору.")
    return False


def kb_main():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать", callback_data=ATestCb(action="create").pack())
    kb.button(text="✏️ Изменить", callback_data=ATestCb(action="edit_list").pack())
    kb.button(text="🗑 Удалить", callback_data=ATestCb(action="delete_list").pack())
    kb.adjust(3)
    return kb.as_markup()


async def send_test_menu(message: Message, test_id: int):
    test = await get_test(test_id)
    if not test:
        await message.answer("❌ Тест не найден.")
        return
    count = len(await get_questions(test_id))
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Название", callback_data=ATestCb(action="title", test_id=test_id).pack())
    kb.button(text="💰 Стоимость", callback_data=ATestCb(action="cost", test_id=test_id).pack())
    kb.button(text="📝 Изменить вопрос", callback_data=ATestCb(action="questions", test_id=test_id).pack())
    if count < MAX_QUESTIONS:
        kb.button(text="➕ Добавить вопрос", callback_data=ATestCb(action="add_q", test_id=test_id).pack())
    if count > 1:
        kb.button(text="➖ Удалить вопрос", callback_data=ATestCb(action="del_q_list", test_id=test_id).pack())
    kb.adjust(1)
    await message.answer(
        f"📘 {test.title}\nСтоимость: {fmt_cost(test.cost)}\nВопросов: {count}",
        reply_markup=kb.as_markup(),
    )


async def ask_question_text(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("mode") == "create":
        header = f"Вопрос {len(data['questions']) + 1}/{data['q_total']}"
    else:
        header = "Вопрос"
    await state.set_state(ATestStates.q_text)
    await message.answer(f"{header}: введите текст вопроса:")


# ---------- Entry ----------

@admin_training.message(F.text == TESTS_ADMIN_BUTTON)
async def tests_menu(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    await state.clear()
    await message.answer("⚙️ Управление тестами", reply_markup=kb_main())


# ---------- Create: название → стоимость → количество ----------

@admin_training.callback_query(ATestCb.filter(F.action == "create"))
async def create_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await state.clear()
    await state.set_state(ATestStates.title)
    await callback.message.answer("Введите название теста:")
    await callback.answer()


@admin_training.message(ATestStates.title)
async def create_title(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer("Название — минимум 2 символа. Введите ещё раз:")
        return
    await state.update_data(title=title)
    await state.set_state(ATestStates.cost)
    await message.answer("Стоимость попытки в кадрах (0 — бесплатно):")


@admin_training.message(ATestStates.cost)
async def create_cost(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    try:
        cost = parse_amount(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}")
        return
    await state.update_data(cost=cost)
    await state.set_state(ATestStates.count)
    await message.answer(f"Сколько вопросов? (1–{MAX_QUESTIONS})")


@admin_training.message(ATestStates.count)
async def create_count(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    try:
        total = int((message.text or "").strip())
    except ValueError:
        total = 0
    if not 1 <= total <= MAX_QUESTIONS:
        await message.answer(f"Нужно число от 1 до {MAX_QUESTIONS}:")
        return
    await state.update_data(mode="create", q_total=total, questions=[])
    await ask_question_text(message, state)


# ---------- Вопрос: текст → 4 варианта → правильный (общее для create / edit_q / add_q) ----------

@admin_training.message(ATestStates.q_text)
async def got_q_text(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Текст вопроса — минимум 2 символа. Введите ещё раз:")
        return
    await state.update_data(cur_text=text)
    await state.set_state(ATestStates.q_options)
    await message.answer("Отправьте 4 варианта ответа одним сообщением — каждый с новой строки:")


@admin_training.message(ATestStates.q_options)
async def got_q_options(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    try:
        options = parse_options(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}")
        return
    await state.update_data(cur_options=options)
    await state.set_state(ATestStates.q_correct)
    kb = InlineKeyboardBuilder()
    for n in range(1, 5):
        kb.button(text=str(n), callback_data=ACorrectCb(option=n).pack())
    kb.adjust(4)
    listing = "\n".join(f"{n}. {opt}" for n, opt in enumerate(options, start=1))
    await message.answer(f"{listing}\n\nКакой вариант правильный?", reply_markup=kb.as_markup())


@admin_training.callback_query(ATestStates.q_correct, ACorrectCb.filter())
async def got_q_correct(callback: CallbackQuery, callback_data: ACorrectCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    data = await state.get_data()
    q = {"text": data["cur_text"], "options": data["cur_options"], "correct": callback_data.option}
    await callback.message.edit_text(f"{callback.message.text}\n\nПравильный: {callback_data.option}")
    await callback.answer()

    mode = data.get("mode")
    if mode == "create":
        questions = data["questions"] + [q]
        if len(questions) < data["q_total"]:
            await state.update_data(questions=questions)
            await ask_question_text(callback.message, state)
            return
        await create_test(data["title"], data["cost"], questions)
        await state.clear()
        await callback.message.answer(f"✅ Тест «{data['title']}» создан: {len(questions)} вопросов.")
        return

    if mode == "edit_q":
        ok = await update_question(data["question_id"], q)
        result = "✅ Вопрос обновлён." if ok else "❌ Вопрос не найден."
    else:  # add_q
        ok = await add_question(data["test_id"], q)
        result = "✅ Вопрос добавлен." if ok else f"❌ Не удалось добавить (максимум {MAX_QUESTIONS})."
    test_id = data["test_id"]
    await state.clear()
    await callback.message.answer(result)
    await send_test_menu(callback.message, test_id)


# ---------- Выбор теста для изменения / удаления ----------

@admin_training.callback_query(ATestCb.filter(F.action.in_({"edit_list", "delete_list"})))
async def pick_test(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    tests = await get_tests_with_counts()
    if not tests:
        await callback.answer("Тестов пока нет.", show_alert=True)
        return
    action = "edit" if callback_data.action == "edit_list" else "delete"
    kb = InlineKeyboardBuilder()
    for test, count in tests:
        kb.button(text=f"{test.title} ({count})", callback_data=ATestCb(action=action, test_id=test.id).pack())
    kb.adjust(1)
    await callback.message.answer("Выберите тест:", reply_markup=kb.as_markup())
    await callback.answer()


@admin_training.callback_query(ATestCb.filter(F.action == "edit"))
async def edit_menu(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await state.clear()
    await send_test_menu(callback.message, callback_data.test_id)
    await callback.answer()


# ---------- Изменение названия / стоимости ----------

@admin_training.callback_query(ATestCb.filter(F.action.in_({"title", "cost"})))
async def edit_field_start(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await state.clear()
    await state.update_data(test_id=callback_data.test_id)
    if callback_data.action == "title":
        await state.set_state(ATestStates.new_title)
        await callback.message.answer("Введите новое название:")
    else:
        await state.set_state(ATestStates.new_cost)
        await callback.message.answer("Введите новую стоимость в кадрах (0 — бесплатно):")
    await callback.answer()


@admin_training.message(ATestStates.new_title)
async def edit_title_apply(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer("Название — минимум 2 символа. Введите ещё раз:")
        return
    test_id = (await state.get_data())["test_id"]
    await state.clear()
    ok = await update_test(test_id, title=title)
    await message.answer("✅ Название обновлено." if ok else "❌ Тест не найден.")
    if ok:
        await send_test_menu(message, test_id)


@admin_training.message(ATestStates.new_cost)
async def edit_cost_apply(message: Message, state: FSMContext):
    if not await admin_only(message, state):
        return
    try:
        cost = parse_amount(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}")
        return
    test_id = (await state.get_data())["test_id"]
    await state.clear()
    ok = await update_test(test_id, cost=cost)
    await message.answer("✅ Стоимость обновлена." if ok else "❌ Тест не найден.")
    if ok:
        await send_test_menu(message, test_id)


# ---------- Вопросы: изменить / добавить / удалить ----------

@admin_training.callback_query(ATestCb.filter(F.action.in_({"questions", "del_q_list"})))
async def question_list(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    questions = await get_questions(callback_data.test_id)
    if not questions:
        await callback.answer("Вопросов нет.", show_alert=True)
        return
    action = "edit" if callback_data.action == "questions" else "delete"
    kb = InlineKeyboardBuilder()
    for i, q in enumerate(questions, start=1):
        kb.button(text=f"{i}. {q.text[:40]}",
                  callback_data=AQuestionCb(action=action, question_id=q.id, test_id=callback_data.test_id).pack())
    kb.adjust(1)
    prompt = "Какой вопрос изменить?" if action == "edit" else "Какой вопрос удалить?"
    await callback.message.answer(prompt, reply_markup=kb.as_markup())
    await callback.answer()


@admin_training.callback_query(AQuestionCb.filter(F.action == "edit"))
async def question_edit_start(callback: CallbackQuery, callback_data: AQuestionCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    q = await get_question(callback_data.question_id)
    if not q:
        await callback.answer("Вопрос не найден.", show_alert=True)
        return
    await state.clear()
    await state.update_data(mode="edit_q", question_id=q.id, test_id=callback_data.test_id)
    options = "\n".join(f"{n}. {opt}" for n, opt in enumerate([q.option_1, q.option_2, q.option_3, q.option_4], start=1))
    await callback.message.answer(f"Сейчас:\n{q.text}\n\n{options}\n\nПравильный: {q.correct}")
    await callback.answer()
    await ask_question_text(callback.message, state)


@admin_training.callback_query(AQuestionCb.filter(F.action == "delete"))
async def question_delete(callback: CallbackQuery, callback_data: AQuestionCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    if not await delete_question(callback_data.question_id):
        await callback.answer("Нельзя удалить последний вопрос.", show_alert=True)
        return
    await callback.answer("🗑 Вопрос удалён")
    await send_test_menu(callback.message, callback_data.test_id)


@admin_training.callback_query(ATestCb.filter(F.action == "add_q"))
async def question_add_start(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    await state.clear()
    await state.update_data(mode="add_q", test_id=callback_data.test_id)
    await callback.answer()
    await ask_question_text(callback.message, state)


# ---------- Удаление теста ----------

@admin_training.callback_query(ATestCb.filter(F.action == "delete"))
async def delete_confirm(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    test = await get_test(callback_data.test_id)
    if not test:
        await callback.answer("Тест не найден.", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, удалить", callback_data=ATestCb(action="delete_yes", test_id=test.id).pack())
    kb.button(text="Отмена", callback_data=ATestCb(action="cancel").pack())
    kb.adjust(2)
    await callback.message.answer(f"Удалить тест «{test.title}» вместе с вопросами и попытками?",
                                  reply_markup=kb.as_markup())
    await callback.answer()


@admin_training.callback_query(ATestCb.filter(F.action == "delete_yes"))
async def delete_apply(callback: CallbackQuery, callback_data: ATestCb, state: FSMContext):
    if not await admin_only(callback, state):
        return
    ok = await delete_test(callback_data.test_id)
    await callback.message.edit_text("🗑 Тест удалён." if ok else "❌ Тест не найден.")
    await callback.answer()


@admin_training.callback_query(ATestCb.filter(F.action == "cancel"))
async def delete_cancel(callback: CallbackQuery):
    await callback.message.edit_text("Отменено.")
    await callback.answer()
```

- [ ] **Step 2: Подключить** — в `handlers/__init__.py`: импорт `from .admin_training import admin_training`; `admin_router.include_router(admin_training)` после `admin_battles`.

- [ ] **Step 3: Кнопки в меню**
  - `keyboards/userkeyboard.py`: `userboard = ReplyKeyboardMarkup(keyboard=user_rows(with_training=True), resize_keyboard=True)`
  - `keyboards/adminkeyboard.py`: в конец `ADMIN_ROWS` добавить `[KeyboardButton(text='Тесты ⚙️')],`; `adminboard = ReplyKeyboardMarkup(keyboard=user_rows(with_training=True) + ADMIN_ROWS, resize_keyboard=True)`

- [ ] **Step 4: Проверить**

Run: `venv_new/Scripts/python.exe -c "import app" && venv_new/Scripts/python.exe -m pytest tests -q`
Expected: OK, PASS.

- [ ] **Step 5: Commit**

```bash
git add handlers/admin_training.py handlers/__init__.py keyboards/userkeyboard.py keyboards/adminkeyboard.py
git commit -m "feat: admin test builder and training buttons in menus

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Ручной чек-лист в Telegram (после всех задач)

Запуск: `venv_new/Scripts/python.exe app.py` (на тестовом боте / копии БД).

1. Новый аккаунт: `/start` → ник → «Понятно!» → меню 3×3. `/start` повторно — ничего. `/menu` — меню.
2. Старый аккаунт: приветствие не приходит, `/menu` показывает новое меню.
3. Добавить танк с годами `1941-1945` → в карточке `1941, 1942, 1943, 1944, 1945`. Изменить годы на `1939, 1941-1942`.
4. Добавить сражение с GIF-картой → в «Список сражений» карта анимирована; «Назад» удаляет анимацию.
5. «Правила» — строка про [Т-70В] и [RENWA].
6. Админ: «Матч-штрафы» → «По нику» → «Добавить штраф» (описание, 2 кадра) → «Штрафы игрока» → «Снять №1» → штраф исчез у игрока.
7. Игрок: «Личный кабинет» → штраф 2 кадра → «Оплатить штраф» → «Кадрами» (при нехватке — alert) → штраф исчез, кадры списаны.
8. То же «Звёздами — 10 ⭐» → инвойс → оплата → «✅ Штраф оплачен».
9. Админ: «Заблокировать 🚫» → «Да» → текст → игрок получает сообщение; любое действие игрока → «🚫 Вы заблокированы». «Разблокировать» → «Нет» → игрок снова работает без уведомления.
10. Админ: «Награды игрока» → переключить ❌→✅ → игрок получает уведомление; в кабинете «выдан ✅».
11. Админ: «Тесты ⚙️» → создать тест (стоимость 1, 2 вопроса) → игрок «Обучение» → пройти с ошибками → «n ошибок из z. Попробуй ещё раз через 24 ч.» → повторный старт → «Попробуй через 23 ч …». Пройти другой тест без ошибок → в кабинете 🟢, повторный старт → «Тест уже пройден».
12. «отмена» посреди создания теста — состояние сброшено, тест не создан.

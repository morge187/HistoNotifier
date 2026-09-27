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

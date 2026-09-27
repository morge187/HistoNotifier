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

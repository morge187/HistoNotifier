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

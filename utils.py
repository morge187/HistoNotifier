import math
import re
from datetime import datetime, timedelta


def fmt_points(value) -> str:
    """Форматирует очки: целые без дробной части (8), дробные как есть (8.5)."""
    value = round(float(value or 0), 2)
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


# ── «Мои кадры»: мемные эмодзи по количеству кадров ──────────────────────────
# (порог, эмодзи, подпись) — от большего к меньшему, берётся первый подходящий.
CADR_TIERS = (
    (200, "🐐", "Двести! Ты уже не игрок, ты часть истории."),
    (150, "🛸", "Сто пятьдесят! Кадры кончились, началась фантастика."),
    (100, "🏆", "СОТКА! Можно открывать собственный музей."),
    (90, "🔥", "Девяносто! Казна дымится."),
    (80, "🚀", "Восемьдесят! Взлёт без тормозов."),
    (70, "👑", "Семьдесят! Ваше благородие."),
    (60, "🎉", "Шестьдесят! Бухгалтерия нервно курит в сторонке."),
    (50, "🎊", "Полтинник! Добро пожаловать в элиту."),
    (40, "💎", "Сорок! Кадры уже поблёскивают."),
    (30, "🥳", "Тридцатка! Есть повод отпраздновать."),
    (20, "🪙", "Двадцатка! Копилка приятно звенит."),
    (10, "💴", "Первая десятка! Уже можно копить на гусеницы."),
)


def cadr_tier(value) -> tuple:
    """Возвращает (эмодзи, мемную подпись) для количества кадров."""
    value = round(float(value or 0), 2)
    for threshold, emoji, phrase in CADR_TIERS:
        if value >= threshold:
            return emoji, phrase
    if value <= 0:
        return "", "Кадров пока нет — самое время заглянуть на ивент."
    return "", "До первой десятки осталось совсем чуть-чуть!"


def cadr_message(value) -> str:
    """Готовый текст для кнопки «Мои кадры» вместе с эмодзи и подписью."""
    emoji, phrase = cadr_tier(value)
    text = f"У вас {fmt_points(value)} кадров{emoji}"
    if phrase:
        text = f"{text}\n{phrase}"
    return text


# ── Нормализация текста для поиска ───────────────────────────────────────────

def normalize_text(text) -> str:
    """Нижний регистр, ё → е, лишние пробелы убраны."""
    return " ".join(str(text or "").replace("ё", "е").replace("Ё", "Е").lower().split())


def loose_text(text) -> str:
    """Только буквы и цифры: «Т-34-85» и «Т 34 85» дают одинаковый результат."""
    return "".join(ch for ch in normalize_text(text) if ch.isalnum())


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

def fmt_points(value) -> str:
    """Форматирует очки: целые без дробной части (8), дробные как есть (8.5)."""
    value = round(float(value or 0), 2)
    if value == int(value):
        return str(int(value))
    return f"{value:g}"

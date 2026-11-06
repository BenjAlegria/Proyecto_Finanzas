"""Validación y cálculos de presupuestos compartidos por ambos modos."""
from datetime import date


def validate_month(month):
    try:
        parsed = date.fromisoformat(month + "-01")
        if f"{parsed.year:04d}-{parsed.month:02d}" != month:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Escribe un mes válido: AAAA-MM.") from None
    return month


def validate_budget(category, amount, month, scope, allowed=None):
    from nexo.data import EXPENSE_CATEGORIES
    validate_month(month)
    if scope not in ("Personal", "Familiar") or category not in (EXPENSE_CATEGORIES if allowed is None else allowed):
        raise ValueError("Selecciona una categoría de egreso y un ámbito válidos.")
    if type(amount) is not int or not 0 < amount <= 9223372036854775807:
        raise ValueError("El límite debe ser un entero CLP positivo dentro del rango permitido.")


def budget_summary(store, month, scope):
    """Read fresh movements each time; income never offsets expenses."""
    validate_month(month)
    result = []
    for category, amount in store.list_budgets(month, scope).items():
        used = store.budget_spent(category, month, scope)
        state = ("exceeded" if used > amount else "reached" if used == amount
                 else "warning" if used * 100 >= amount * 80 else "normal")
        result.append(dict(category=category, amount=amount, used=used,
                           remaining=amount - used, percent=used / amount * 100,
                           state=state))
    return result

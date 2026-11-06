from datetime import date, datetime, timezone

INCOME_CATEGORIES = ("Sueldo", "Ventas", "Trabajo independiente", "Bonos", "Regalos recibidos", "Otros ingresos")
EXPENSE_CATEGORIES = ("Alimentación", "Vivienda", "Transporte", "Servicios básicos", "Salud", "Educación", "Entretenimiento", "Compras", "Deudas", "Otros egresos")
# Preserve the internal Gasto value used by totals and budgets.
CATEGORIES_BY_KIND = {"Ingreso": INCOME_CATEGORIES, "Gasto": EXPENSE_CATEGORIES}
KIND_LABELS = {"Ingreso": "Ingreso", "Gasto": "Egreso"}
KIND_VALUES = {label: value for value, label in KIND_LABELS.items()}
CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES


def movement_order(movement):
    """Transaction date, UTC registration time, then immutable session ID."""
    return movement["date"], movement["registered_at"], movement["id"]


def clp(amount):
    return ("-$" if amount < 0 else "$") + f"{abs(amount):,}".replace(",", ".")


def validate_movement(kind, scope, amount, day, category, description):
    day = date.fromisoformat(day).isoformat()
    if kind not in CATEGORIES_BY_KIND or scope not in ("Personal", "Familiar"):
        raise ValueError("Selecciona tipo y ámbito válidos.")
    if type(amount) is not int or not 0 < amount <= 9223372036854775807:
        raise ValueError("El monto debe ser un entero positivo dentro del rango permitido.")
    if category not in CATEGORIES_BY_KIND[kind]:
        raise ValueError("Selecciona una categoría válida para el tipo de movimiento.")
    if not description.strip():
        raise ValueError("Escribe una descripción.")
    return day


class DemoStore:
    user = "Camila"

    def __init__(self):
        self.home = "Hogar Rivera"
        self.budgets = {"Alimentación": 350000, "Vivienda": 600000, "Transporte": 120000, "Entretenimiento": 80000}
        self.movements = []
        self._next_id = 1
        for kind, scope, amount, category, description, author in (
            ("Ingreso", "Familiar", 1800000, "Sueldo", "Aporte mensual", "Camila"),
            ("Ingreso", "Familiar", 650000, "Sueldo", "Aporte al hogar", "Diego"),
            ("Gasto", "Familiar", 520000, "Vivienda", "Arriendo", "Diego"),
            ("Gasto", "Familiar", 186500, "Alimentación", "Supermercado", "Camila"),
            ("Gasto", "Familiar", 45000, "Transporte", "Combustible", "Camila"),
            ("Ingreso", "Personal", 320000, "Trabajo independiente", "Proyecto personal", "Camila"),
            ("Gasto", "Personal", 28900, "Entretenimiento", "Libros", "Camila"),
        ):
            self.add(kind, scope, amount, date.today().isoformat(), category, description, author)

    def add(self, kind, scope, amount, day, category, description, author=None):
        day = validate_movement(kind, scope, amount, day, category, description)
        self.movements.append(dict(kind=kind, scope=scope, amount=amount, date=day,
                                    category=category, description=description.strip(),
                                    author=author or self.user,
                                    registered_at=datetime.now(timezone.utc), id=self._next_id))
        self._next_id += 1
        # Keep canonical data and every filtered view in the same order.
        self.movements.sort(key=movement_order, reverse=True)

    def visible(self, scope=None, month=None, category=None):
        return sorted((m for m in self.movements
                       if (m["scope"] == "Familiar" or m["author"] == self.user)
                       and (scope is None or m["scope"] == scope)
                       and (month is None or m["date"].startswith(month))
                       and (category is None or m["category"] == category)),
                      key=movement_order, reverse=True)

    def totals(self, scope, month):
        rows = self.visible(scope, month)
        income = sum(m["amount"] for m in rows if m["kind"] == "Ingreso")
        expense = sum(m["amount"] for m in rows if m["kind"] == "Gasto")
        return income, expense, income - expense

    def set_home(self, value):
        if not value.strip():
            raise ValueError("Escribe un nombre para el hogar.")
        self.home = value.strip()

    def set_budget(self, category, amount):
        if category not in EXPENSE_CATEGORIES or type(amount) is not int or not 0 < amount <= 9223372036854775807:
            raise ValueError("Selecciona categoría y límite entero positivo válido.")
        self.budgets[category] = amount

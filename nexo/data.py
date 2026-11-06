from datetime import date, datetime, timezone
from nexo.budgets import validate_budget, validate_month
from nexo.categories import MemoryCategories

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


def validate_movement(kind, scope, amount, day, category, description, allowed=None):
    day = date.fromisoformat(day).isoformat()
    if kind not in CATEGORIES_BY_KIND or scope not in ("Personal", "Familiar"):
        raise ValueError("Selecciona tipo y ámbito válidos.")
    if type(amount) is not int or not 0 < amount <= 9223372036854775807:
        raise ValueError("El monto debe ser un entero positivo dentro del rango permitido.")
    if category not in (CATEGORIES_BY_KIND[kind] if allowed is None else allowed):
        raise ValueError("Selecciona una categoría válida para el tipo de movimiento.")
    if not description.strip():
        raise ValueError("Escribe una descripción.")
    return day


class DemoStore:
    user = "Camila"

    def __init__(self):
        self.catalog = MemoryCategories(CATEGORIES_BY_KIND)
        self.home = "Hogar Rivera"
        month = date.today().strftime("%Y-%m")
        self._budgets = {(category, month, "Familiar"): amount for category, amount in
                         {"Alimentación": 350000, "Vivienda": 600000, "Transporte": 120000, "Entretenimiento": 80000}.items()}
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
        day = validate_movement(kind, scope, amount, day, category, description, self.category_names(kind, scope))
        self.movements.append(dict(kind=kind, scope=scope, amount=amount, date=day,
                                    category=category, description=description.strip(),
                                    author=author or self.user, category_id=self.category_identity(category, kind, scope),
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

    @property
    def budgets(self):
        return self.list_budgets(date.today().strftime("%Y-%m"), "Familiar")

    def list_budgets(self, month, scope):
        validate_month(month)
        return dict(sorted((category, amount) for (category, saved_month, saved_scope), amount
                           in self._budgets.items() if saved_month == month and saved_scope == scope))

    def create_budget(self, category, amount, month, scope):
        validate_budget(category, amount, month, scope, self.category_names("Gasto", scope))
        key = (category, month, scope)
        if key in self._budgets:
            raise ValueError("Ya existe un presupuesto para esa categoría, mes y ámbito.")
        self._budgets[key] = amount

    def update_budget(self, category, amount, month, scope):
        validate_budget(category, amount, month, scope, self.category_names("Gasto", scope))
        key = (category, month, scope)
        if key not in self._budgets:
            raise ValueError("El presupuesto ya no existe.")
        self._budgets[key] = amount

    def delete_budget(self, category, month, scope):
        key = (category, month, scope)
        if key not in self._budgets:
            raise ValueError("El presupuesto ya no existe.")
        del self._budgets[key]

    def set_budget(self, category, amount):
        """Compatibility with the previous current-month family settings API."""
        month = date.today().strftime("%Y-%m")
        if category in self.list_budgets(month, "Familiar"):
            self.update_budget(category, amount, month, "Familiar")
        else:
            self.create_budget(category, amount, month, "Familiar")

    def list_categories(self, kind=None, scope=None, active_only=True):
        return self.catalog.list(kind, scope, active_only)

    def category_names(self, kind, scope, active_only=True):
        return tuple(row["name"] for row in self.list_categories(kind, scope, active_only))

    def category_identity(self, name, kind, scope):
        return next(row["id"] for row in self.list_categories(kind, scope, False) if row["name"] == name)

    def create_category(self, name, kind, scope):
        return self.catalog.create(name, kind, scope)

    def _protect_category(self, identity):
        row = self.catalog.get(identity)
        if row["kind"] == "Gasto" and any(c == row["name"] and s == row["scope"] for c, m, s in self._budgets):
            raise ValueError("La categoría tiene presupuestos vinculados. Conserva esos presupuestos o elimínalos antes de cambiarla.")
        return row

    def rename_category(self, identity, name):
        self._protect_category(identity)
        self.catalog.rename(identity, name)

    def deactivate_category(self, identity):
        self._protect_category(identity)["active"] = False

    def activate_category(self, identity):
        self.catalog.get(identity)["active"] = True

    def budget_spent(self, category, month, scope):
        identity = self.category_identity(category, "Gasto", scope)
        return sum(m["amount"] for m in self.visible(scope, month)
                   if m["kind"] == "Gasto" and m["category_id"] == identity)

"""Persistencia local de un solo usuario. Nunca carga datos de demostración."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from nexo.data import DemoStore, EXPENSE_CATEGORIES, validate_movement


class StorageError(Exception):
    """Error recuperable de almacenamiento, sin exponer datos financieros."""


class SQLiteStore:
    user = "Usuario local"
    # Pure calculation shared with the demo; no inheritance or fixture loading.
    totals = DemoStore.totals

    def __init__(self, path):
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError("No se pudo acceder al directorio de datos locales.") from exc
        with self._connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('Ingreso', 'Gasto')),
                scope TEXT NOT NULL CHECK(scope IN ('Personal', 'Familiar')),
                amount INTEGER NOT NULL CHECK(typeof(amount) = 'integer' AND amount > 0),
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL CHECK(length(trim(description)) > 0),
                registered_at TEXT NOT NULL
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS movements_order ON movements(date DESC, registered_at DESC, id DESC)")
            db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY, amount INTEGER NOT NULL
                CHECK(typeof(amount) = 'integer' AND amount > 0))""")

    @contextmanager
    def _connection(self):
        db = None
        try:
            db = sqlite3.connect(str(self.path), timeout=3)
            db.row_factory = sqlite3.Row
            with db:
                yield db
        except (sqlite3.Error, OSError) as exc:
            raise StorageError("No se pudo leer o guardar la información local. Revisa el espacio y los permisos, y vuelve a intentar.") from exc
        finally:
            if db is not None:
                db.close()

    @property
    def home(self):
        with self._connection() as db:
            row = db.execute("SELECT value FROM settings WHERE key = ?", ("home",)).fetchone()
        return row[0] if row else "Mi hogar"

    def set_home(self, value):
        if not value.strip():
            raise ValueError("Escribe un nombre para el hogar.")
        with self._connection() as db:
            db.execute("INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", ("home", value.strip()))

    @property
    def budgets(self):
        with self._connection() as db:
            return dict(db.execute("SELECT category, amount FROM budgets ORDER BY category").fetchall())

    def set_budget(self, category, amount):
        if category not in EXPENSE_CATEGORIES or type(amount) is not int or not 0 < amount <= 9223372036854775807:
            raise ValueError("Selecciona categoría y límite entero positivo válido.")
        with self._connection() as db:
            db.execute("INSERT INTO budgets(category, amount) VALUES (?, ?) ON CONFLICT(category) DO UPDATE SET amount = excluded.amount", (category, amount))

    @staticmethod
    def _movement(row):
        result = dict(row)
        try:
            result["registered_at"] = datetime.fromisoformat(result["registered_at"])
            validate_movement(result["kind"], result["scope"], result["amount"], result["date"], result["category"], result["description"])
            if result["registered_at"].tzinfo is None:
                raise ValueError("Marca sin zona horaria")
        except (ValueError, TypeError) as exc:
            raise StorageError("Hay un movimiento local con formato inválido. Conserva una copia de la base antes de repararla.") from exc
        result["author"] = SQLiteStore.user
        return result

    def visible(self, scope=None, month=None, category=None):
        conditions, params = [], []
        if scope is not None:
            conditions.append("scope = ?")
            params.append(scope)
        if month is not None:
            conditions.append("substr(date, 1, 7) = ?")
            params.append(month)
        if category is not None:
            conditions.append("category = ?")
            params.append(category)
        sql = "SELECT * FROM movements"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY date DESC, registered_at DESC, id DESC"
        with self._connection() as db:
            return [self._movement(row) for row in db.execute(sql, params).fetchall()]

    def get(self, movement_id):
        with self._connection() as db:
            row = db.execute("SELECT * FROM movements WHERE id = ?", (movement_id,)).fetchone()
        if row is None:
            raise ValueError("El movimiento ya no existe.")
        return self._movement(row)

    def add(self, kind, scope, amount, day, category, description):
        day = validate_movement(kind, scope, amount, day, category, description)
        created = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        with self._connection() as db:
            cursor = db.execute("""INSERT INTO movements
                (kind, scope, amount, date, category, description, registered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (kind, scope, amount, day, category, description.strip(), created))
            return cursor.lastrowid

    def update(self, movement_id, kind, scope, amount, day, category, description):
        day = validate_movement(kind, scope, amount, day, category, description)
        with self._connection() as db:
            cursor = db.execute("""UPDATE movements SET kind = ?, scope = ?, amount = ?,
                date = ?, category = ?, description = ? WHERE id = ?""",
                (kind, scope, amount, day, category, description.strip(), movement_id))
            if cursor.rowcount != 1:
                raise ValueError("El movimiento ya no existe.")

    def delete(self, movement_id):
        with self._connection() as db:
            cursor = db.execute("DELETE FROM movements WHERE id = ?", (movement_id,))
            if cursor.rowcount != 1:
                raise ValueError("El movimiento ya no existe.")

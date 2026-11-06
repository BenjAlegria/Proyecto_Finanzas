"""Persistencia local de un solo usuario. Nunca carga datos de demostración."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
import sqlite3

from nexo.data import DemoStore, CATEGORIES_BY_KIND, validate_movement
from nexo.categories import category_name, name_key, validate_type_scope
from nexo.budgets import validate_budget, validate_month


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
            # Explicit transaction includes DDL and migration. Failure rolls back all steps.
            db.execute("BEGIN IMMEDIATE")
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
            self._migrate_budgets(db)
            try:
                self._migrate_categories(db)
            except ValueError as exc:
                raise StorageError("No se pudo migrar el catálogo. Los cambios se revirtieron; conserva la base para revisarla.") from exc

    @staticmethod
    def _migrate_categories(db):
        db.execute("""CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, name_key TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('Ingreso', 'Gasto')),
            scope TEXT NOT NULL CHECK(scope IN ('Personal', 'Familiar')),
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
            custom INTEGER NOT NULL CHECK(custom IN (0,1)), UNIQUE(name_key, kind, scope))""")
        for table in ("movements", "monthly_budgets"):
            if "category_id" not in [row[1] for row in db.execute("PRAGMA table_info(" + table + ")")]:
                db.execute("ALTER TABLE " + table + " ADD COLUMN category_id INTEGER REFERENCES categories(id)")
        if db.execute("SELECT value FROM settings WHERE key = ?", ("categories_v1",)).fetchone():
            return
        for scope in ("Personal", "Familiar"):
            for kind, names in CATEGORIES_BY_KIND.items():
                for name in names:
                    db.execute("INSERT OR IGNORE INTO categories(name,name_key,kind,scope,custom) VALUES (?,?,?,?,0)",
                               (name, name_key(name), kind, scope))
        for table in ("movements", "monthly_budgets"):
            kind_sql = "kind" if table == "movements" else "'Gasto'"
            rows = db.execute("SELECT DISTINCT category, " + kind_sql + ", scope FROM " + table).fetchall()
            for name, kind, scope in rows:
                db.execute("INSERT OR IGNORE INTO categories(name,name_key,kind,scope,custom) VALUES (?,?,?,?,1)",
                           (name, name_key(name), kind, scope))
                identity = db.execute("SELECT id FROM categories WHERE name_key=? AND kind=? AND scope=?",
                                      (name_key(name), kind, scope)).fetchone()[0]
                db.execute("UPDATE " + table + " SET category_id=? WHERE category=? AND " + kind_sql + "=? AND scope=?",
                           (identity, name, kind, scope))
        db.execute("INSERT INTO settings(key,value) VALUES (?,?)", ("categories_v1", "1"))

    @staticmethod
    def _migrate_budgets(db):
        db.execute("""CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY, amount INTEGER NOT NULL
                CHECK(typeof(amount) = 'integer' AND amount > 0))""")
        db.execute("""CREATE TABLE IF NOT EXISTS monthly_budgets (
            category TEXT NOT NULL,
            month TEXT NOT NULL,
            scope TEXT NOT NULL CHECK(scope IN ('Personal', 'Familiar')),
            amount INTEGER NOT NULL CHECK(typeof(amount) = 'integer' AND amount > 0),
            PRIMARY KEY(category, month, scope))""")
        marker = "monthly_budgets_v1"
        if db.execute("SELECT value FROM settings WHERE key = ?", (marker,)).fetchone() is None:
            # Legacy limits applied only to the current month and family scope.
            month = date.today().strftime("%Y-%m")
            rows = db.execute("SELECT category, amount FROM budgets").fetchall()
            for category, amount in rows:
                try:
                    validate_budget(category, amount, month, "Familiar")
                except ValueError as exc:
                    raise StorageError("No se pudo migrar un límite antiguo inválido. No se modificaron los datos.") from exc
                db.execute("INSERT INTO monthly_budgets(category, month, scope, amount) VALUES (?, ?, ?, ?)",
                           (category, month, "Familiar", amount))
            db.execute("INSERT INTO settings(key, value) VALUES (?, ?)", (marker, month))
        # Keep the old table as a migration record; never re-import on restart.

    @contextmanager
    def _connection(self):
        db = None
        try:
            db = sqlite3.connect(str(self.path), timeout=3)
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
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
        return self.list_budgets(date.today().strftime("%Y-%m"), "Familiar")

    def list_budgets(self, month, scope):
        validate_month(month)
        with self._connection() as db:
            return dict(db.execute("SELECT category, amount FROM monthly_budgets WHERE month = ? AND scope = ? ORDER BY category", (month, scope)).fetchall())

    def create_budget(self, category, amount, month, scope):
        validate_budget(category, amount, month, scope, self.category_names("Gasto", scope))
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            identity = self._category_for_write(db, category, "Gasto", scope)
            try:
                db.execute("INSERT INTO monthly_budgets(category, month, scope, amount, category_id) VALUES (?, ?, ?, ?, ?)",
                           (category, month, scope, amount, identity))
            except sqlite3.IntegrityError as exc:
                raise ValueError("Ya existe un presupuesto para esa categoría, mes y ámbito.") from exc

    def update_budget(self, category, amount, month, scope):
        validate_budget(category, amount, month, scope, self.category_names("Gasto", scope))
        with self._connection() as db:
            cursor = db.execute("UPDATE monthly_budgets SET amount = ? WHERE category = ? AND month = ? AND scope = ?",
                                (amount, category, month, scope))
            if cursor.rowcount != 1:
                raise ValueError("El presupuesto ya no existe.")

    def delete_budget(self, category, month, scope):
        validate_budget(category, 1, month, scope, self.category_names("Gasto", scope, False))
        with self._connection() as db:
            cursor = db.execute("DELETE FROM monthly_budgets WHERE category = ? AND month = ? AND scope = ?", (category, month, scope))
            if cursor.rowcount != 1:
                raise ValueError("El presupuesto ya no existe.")

    def set_budget(self, category, amount):
        """Compatibility API for the former current-month family limit."""
        month = date.today().strftime("%Y-%m")
        if category in self.list_budgets(month, "Familiar"):
            self.update_budget(category, amount, month, "Familiar")
        else:
            self.create_budget(category, amount, month, "Familiar")

    @staticmethod
    def _movement(row):
        result = dict(row)
        try:
            result["registered_at"] = datetime.fromisoformat(result["registered_at"])
            validate_movement(result["kind"], result["scope"], result["amount"], result["date"], result["category"], result["description"], (result["category"],))
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
        day = validate_movement(kind, scope, amount, day, category, description, self.category_names(kind, scope))
        created = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            identity = self._category_for_write(db, category, kind, scope)
            cursor = db.execute("""INSERT INTO movements
                (kind, scope, amount, date, category, description, registered_at, category_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (kind, scope, amount, day, category, description.strip(), created, identity))
            return cursor.lastrowid

    def update(self, movement_id, kind, scope, amount, day, category, description):
        day = validate_movement(kind, scope, amount, day, category, description, (category,))
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM movements WHERE id=?", (movement_id,)).fetchone()
            if old is None:
                raise ValueError("El movimiento ya no existe.")
            # Keep a historical/inactive name when editing other fields of that record.
            identity = old["category_id"] if (old["kind"], old["scope"], old["category"]) == (kind, scope, category) else self._category_for_write(db, category, kind, scope)
            cursor = db.execute("""UPDATE movements SET kind = ?, scope = ?, amount = ?,
                date = ?, category = ?, description = ?, category_id = ? WHERE id = ?""",
                (kind, scope, amount, day, category, description.strip(), identity, movement_id))
            if cursor.rowcount != 1:
                raise ValueError("El movimiento ya no existe.")

    def delete(self, movement_id):
        with self._connection() as db:
            cursor = db.execute("DELETE FROM movements WHERE id = ?", (movement_id,))
            if cursor.rowcount != 1:
                raise ValueError("El movimiento ya no existe.")

    def list_categories(self, kind=None, scope=None, active_only=True):
        with self._connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM categories ORDER BY custom, id").fetchall()
                    if (kind is None or row["kind"] == kind) and (scope is None or row["scope"] == scope)
                    and (not active_only or row["active"])]

    category_names = DemoStore.category_names

    @staticmethod
    def _category_for_write(db, name, kind, scope):
        row = db.execute("SELECT id FROM categories WHERE name=? AND kind=? AND scope=? AND active=1", (name, kind, scope)).fetchone()
        if row is None:
            raise ValueError("Selecciona una categoría activa del tipo y ámbito correspondientes.")
        return row[0]

    def create_category(self, name, kind, scope):
        validate_type_scope(kind, scope)
        name = category_name(name)
        with self._connection() as db:
            try:
                return db.execute("INSERT INTO categories(name,name_key,kind,scope,custom) VALUES (?,?,?,?,1)",
                                  (name, name_key(name), kind, scope)).lastrowid
            except sqlite3.IntegrityError as exc:
                raise ValueError("Ya existe esa categoría en el mismo tipo y ámbito, incluso si está inactiva.") from exc

    @staticmethod
    def _protect_category(db, identity):
        row = db.execute("SELECT * FROM categories WHERE id=?", (identity,)).fetchone()
        if row is None:
            raise ValueError("La categoría ya no existe.")
        if db.execute("SELECT 1 FROM monthly_budgets WHERE category_id=? LIMIT 1", (identity,)).fetchone():
            raise ValueError("La categoría tiene presupuestos vinculados. No se puede renombrar ni desactivar.")
        return row

    def rename_category(self, identity, name):
        name = category_name(name)
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._protect_category(db, identity)
            if not row["custom"]:
                raise ValueError("Las categorías predeterminadas no se pueden renombrar.")
            try:
                db.execute("UPDATE categories SET name=?, name_key=? WHERE id=?", (name, name_key(name), identity))
            except sqlite3.IntegrityError as exc:
                raise ValueError("Ya existe una categoría con ese nombre, tipo y ámbito.") from exc

    def deactivate_category(self, identity):
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._protect_category(db, identity)
            db.execute("UPDATE categories SET active=0 WHERE id=?", (identity,))

    def activate_category(self, identity):
        with self._connection() as db:
            cursor = db.execute("UPDATE categories SET active=1 WHERE id=?", (identity,))
            if cursor.rowcount != 1:
                raise ValueError("La categoría ya no existe.")

    def budget_spent(self, category, month, scope):
        with self._connection() as db:
            identity = db.execute("SELECT id FROM categories WHERE name=? AND kind='Gasto' AND scope=?", (category, scope)).fetchone()
            if identity is None:
                return 0
            # Python sum avoids SQLite SUM overflowing when many large CLP amounts exist.
            return sum(row[0] for row in db.execute("SELECT amount FROM movements WHERE category_id=? AND kind='Gasto' AND scope=? AND substr(date,1,7)=?", (identity[0], scope, month)))

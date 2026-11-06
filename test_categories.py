from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest
from unittest.mock import patch
from nexo.storage import SQLiteStore, StorageError
from nexo.data import DemoStore
from nexo.budgets import budget_summary


class CategoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "categories.sqlite3"
        self.store = SQLiteStore(self.path)

    def test_create_persist_and_duplicate_normalization(self):
        identity = self.store.create_category("  Mi   proyecto  ", "Ingreso", "Personal")
        self.assertIn("Mi proyecto", SQLiteStore(self.path).category_names("Ingreso", "Personal"))
        for name in ("mi proyecto", "MI PROYECTO", "  Mi proyecto "):
            with self.assertRaises(ValueError):
                self.store.create_category(name, "Ingreso", "Personal")
        self.store.create_category("Mi proyecto", "Ingreso", "Familiar")
        self.store.create_category("Mi proyecto", "Gasto", "Personal")
        self.assertTrue(any(r["id"] == identity for r in self.store.list_categories()))
        for name in ("", "  ", "x" * 61):
            with self.assertRaises(ValueError):
                self.store.create_category(name, "Gasto", "Personal")

    def test_rename_and_historical_snapshot(self):
        identity = self.store.create_category("Mascotas", "Gasto", "Personal")
        movement = self.store.add("Gasto", "Personal", 10000, "2026-11-06", "Mascotas", "Veterinario")
        original = self.store.get(movement)
        self.store.rename_category(identity, "Cuidado animal")
        self.assertEqual(self.store.get(movement), original)
        self.store.update(movement, "Gasto", "Personal", 12000, "2026-11-06", "Mascotas", "Editado")
        self.assertEqual(self.store.get(movement)["category_id"], identity)
        self.store.create_budget("Cuidado animal", 20000, "2026-11", "Personal")
        self.assertEqual(budget_summary(self.store, "2026-11", "Personal")[0]["used"], 12000)
        self.assertEqual(self.store.get(movement)["category"], "Mascotas")
        self.assertIn("Cuidado animal", SQLiteStore(self.path).category_names("Gasto", "Personal"))

    def test_deactivation_keeps_history_and_can_edit_old_record(self):
        identity = self.store.create_category("Mascotas", "Gasto", "Personal")
        movement = self.store.add("Gasto", "Personal", 100, "2026-11-06", "Mascotas", "Histórico")
        self.store.deactivate_category(identity)
        self.assertNotIn("Mascotas", SQLiteStore(self.path).category_names("Gasto", "Personal"))
        self.assertEqual(self.store.get(movement)["category"], "Mascotas")
        self.store.update(movement, "Gasto", "Personal", 200, "2026-11-06", "Mascotas", "Editado")
        self.assertEqual(self.store.totals("Personal", "2026-11"), (0, 200, -200))
        with self.assertRaises(ValueError):
            self.store.add("Gasto", "Personal", 10, "2026-11-06", "Mascotas", "Nuevo")
        with self.assertRaises(ValueError):
            self.store.create_category("mascotas", "Gasto", "Personal")

    def test_type_and_scope_validation(self):
        self.store.create_category("Servicios profesionales", "Ingreso", "Personal")
        self.store.add("Ingreso", "Personal", 100, "2026-11-06", "Servicios profesionales", "Ingreso")
        for kind, scope in (("Gasto", "Personal"), ("Ingreso", "Familiar")):
            with self.assertRaises(ValueError):
                self.store.add(kind, scope, 10, "2026-11-06", "Servicios profesionales", "Inválido")
        with self.assertRaises(ValueError):
            self.store.create_budget("Servicios profesionales", 100, "2026-11", "Personal")

    def test_protect_budgets_and_defaults(self):
        identity = self.store.create_category("Mascotas", "Gasto", "Personal")
        self.store.create_budget("Mascotas", 1000, "2025-01", "Personal")
        with self.assertRaises(ValueError):
            self.store.rename_category(identity, "Otro nombre")
        with self.assertRaises(ValueError):
            self.store.deactivate_category(identity)
        self.assertEqual(self.store.list_budgets("2025-01", "Personal"), {"Mascotas": 1000})
        default = next(r for r in self.store.list_categories("Gasto", "Personal") if not r["custom"])
        with self.assertRaises(ValueError):
            self.store.rename_category(default["id"], "No permitido")
        self.store.delete_budget("Mascotas", "2025-01", "Personal")
        self.store.deactivate_category(identity)

    def test_migration_preserves_old_rows_and_is_repeatable(self):
        # Create precisely the pre-catalog tables, without category_id columns.
        legacy_path = Path(self.temp.name) / "legacy.sqlite3"
        with closing(sqlite3.connect(legacy_path)) as db:
            db.executescript("""
                CREATE TABLE movements(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, scope TEXT,
                    amount INTEGER, date TEXT, category TEXT, description TEXT, registered_at TEXT);
                INSERT INTO movements VALUES(42,'Gasto','Personal',1234,'2026-11-06','Salud','Histórico','2026-11-06T10:00:00+00:00');
                CREATE TABLE monthly_budgets(category TEXT, month TEXT, scope TEXT, amount INTEGER, PRIMARY KEY(category,month,scope));
                INSERT INTO monthly_budgets VALUES('Salud','2026-11','Personal',2000);
                CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
                INSERT INTO settings VALUES('monthly_budgets_v1','2026-11');
            """)
            before = db.execute("SELECT * FROM movements").fetchall()
        migrated = SQLiteStore(legacy_path)
        self.assertEqual(migrated.get(42)["amount"], 1234)
        self.assertEqual(budget_summary(migrated, "2026-11", "Personal")[0]["used"], 1234)
        count = len(migrated.list_categories(active_only=False))
        reopened = SQLiteStore(legacy_path)
        self.assertEqual(len(reopened.list_categories(active_only=False)), count)
        with closing(sqlite3.connect(legacy_path)) as db:
            self.assertEqual(db.execute("SELECT id,kind,scope,amount,date,category,description,registered_at FROM movements").fetchall(), before)

    def test_demo_is_isolated(self):
        before = self.path.read_bytes()
        demo = DemoStore()
        identity = demo.create_category("Mascotas", "Gasto", "Personal")
        demo.add("Gasto", "Personal", 100, "2026-11-06", "Mascotas", "Demo")
        demo.rename_category(identity, "Animales")
        demo.create_budget("Animales", 200, "2026-11", "Personal")
        self.assertEqual(budget_summary(demo, "2026-11", "Personal")[0]["used"], 100)
        with self.assertRaises(ValueError):
            demo.deactivate_category(identity)
        self.assertEqual(self.path.read_bytes(), before)

    def test_duplicate_rename_and_migration_rollback(self):
        first = self.store.create_category("Mascotas", "Gasto", "Personal")
        self.store.create_category("Viajes", "Gasto", "Personal")
        with self.assertRaises(ValueError):
            self.store.rename_category(first, " VIAJES ")
        self.assertIn("Mascotas", self.store.category_names("Gasto", "Personal"))
        movement = self.store.add("Gasto", "Personal", 10, "2026-11-06", "Mascotas", "Conservar")
        before = self.store.get(movement)
        migration = SQLiteStore._migrate_categories

        def fail_after_migration(db):
            migration(db)
            db.execute("CREATE TABLE transient_change(id INTEGER)")
            raise ValueError("fallo simulado")

        with patch.object(SQLiteStore, "_migrate_categories", side_effect=fail_after_migration):
            with self.assertRaises(StorageError):
                SQLiteStore(self.path)
        self.assertEqual(SQLiteStore(self.path).get(movement), before)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='transient_change'").fetchone())

    def test_reactivation_preserves_identity_history_and_persists(self):
        identity = self.store.create_category("Mascotas", "Gasto", "Personal")
        movement = self.store.add("Gasto", "Personal", 100, "2026-11-06", "Mascotas", "Conservar")
        before = self.store.get(movement)
        self.store.deactivate_category(identity)
        self.store.activate_category(identity)
        reopened = SQLiteStore(self.path)
        self.assertIn("Mascotas", reopened.category_names("Gasto", "Personal"))
        self.assertEqual(reopened.get(movement), before)
        self.assertEqual(next(r["id"] for r in reopened.list_categories("Gasto", "Personal") if r["name"] == "Mascotas"), identity)
        reopened.create_budget("Mascotas", 200, "2026-11", "Personal")
        self.assertEqual(budget_summary(reopened, "2026-11", "Personal")[0]["used"], 100)
        with self.assertRaises(ValueError):
            reopened.activate_category(-1)
        demo = DemoStore()
        demo_id = demo.create_category("Mascotas", "Gasto", "Personal")
        demo.deactivate_category(demo_id)
        demo.activate_category(demo_id)
        self.assertIn("Mascotas", demo.category_names("Gasto", "Personal"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Presupuestos y migración con bases temporales, sin tocar datos personales."""
from datetime import date
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from nexo.budgets import budget_summary
from nexo.data import DemoStore
from nexo.storage import SQLiteStore, StorageError


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "local.sqlite3"
        self.store = SQLiteStore(self.path)

    def summary(self):
        return budget_summary(self.store, "2026-10", "Personal")[0]

    def expense(self, amount, day="2026-10-10", category="Alimentación", scope="Personal"):
        return self.store.add("Gasto", scope, amount, day, category, "Egreso de prueba")

    def test_create_edit_delete_and_reopen(self):
        self.store.create_budget("Alimentación", 100000, "2026-10", "Personal")
        self.assertEqual(SQLiteStore(self.path).list_budgets("2026-10", "Personal"), {"Alimentación": 100000})
        self.store.update_budget("Alimentación", 120000, "2026-10", "Personal")
        self.assertEqual(SQLiteStore(self.path).list_budgets("2026-10", "Personal"), {"Alimentación": 120000})
        self.store.delete_budget("Alimentación", "2026-10", "Personal")
        self.assertEqual(SQLiteStore(self.path).list_budgets("2026-10", "Personal"), {})

    def test_duplicate_prevention_and_independent_keys(self):
        self.store.create_budget("Salud", 100, "2026-10", "Personal")
        with self.assertRaises(ValueError):
            self.store.create_budget("Salud", 999, "2026-10", "Personal")
        self.store.create_budget("Salud", 200, "2026-11", "Personal")
        self.store.create_budget("Salud", 300, "2026-10", "Familiar")
        self.assertEqual(self.store.list_budgets("2026-10", "Personal"), {"Salud": 100})
        with sqlite3.connect(self.path) as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO monthly_budgets(category, month, scope, amount) VALUES (?, ?, ?, ?)", ("Salud", "2026-10", "Personal", 999))

    def test_live_expenses_thresholds_edit_and_delete(self):
        self.store.create_budget("Alimentación", 100000, "2026-10", "Personal")
        self.assertEqual(self.summary()["remaining"], 100000)
        movement_id = self.expense(79999)
        self.assertEqual(self.summary()["state"], "normal")
        self.store.update(movement_id, "Gasto", "Personal", 80000, "2026-10-10", "Alimentación", "Editado")
        self.assertEqual(self.summary()["state"], "warning")
        self.assertEqual(self.summary()["remaining"], 20000)
        self.store.update(movement_id, "Gasto", "Personal", 100000, "2026-10-10", "Alimentación", "Editado")
        self.assertEqual(self.summary()["state"], "reached")
        self.expense(1)
        self.assertEqual(self.summary()["state"], "exceeded")
        self.assertEqual(self.summary()["remaining"], -1)
        self.store.delete(movement_id)
        self.assertEqual(self.summary()["used"], 1)
        self.assertEqual(self.summary()["state"], "normal")

    def test_filtering_and_income_never_counts(self):
        self.store.create_budget("Alimentación", 100000, "2026-10", "Personal")
        movement_id = self.expense(15000)
        self.expense(20000, day="2026-11-01")
        self.expense(30000, category="Salud")
        self.expense(40000, scope="Familiar")
        self.store.add("Ingreso", "Personal", 999999, "2026-10-10", "Sueldo", "Ingreso")
        self.assertEqual(self.summary()["used"], 15000)
        self.store.update(movement_id, "Gasto", "Personal", 15000, "2026-09-30", "Alimentación", "Otro mes")
        self.assertEqual(self.summary()["used"], 0)
        self.store.update(movement_id, "Gasto", "Familiar", 15000, "2026-10-10", "Alimentación", "Otro ámbito")
        self.assertEqual(self.summary()["used"], 0)
        self.store.update(movement_id, "Ingreso", "Personal", 15000, "2026-10-10", "Ventas", "Ahora ingreso")
        self.assertEqual(self.summary()["used"], 0)

    def test_invalid_values(self):
        for category, amount, month, scope in (
            ("Sueldo", 10, "2026-10", "Personal"), ("Salud", 0, "2026-10", "Personal"),
            ("Salud", -1, "2026-10", "Personal"), ("Salud", 1.5, "2026-10", "Personal"),
            ("Salud", True, "2026-10", "Personal"), ("Salud", 2**63, "2026-10", "Personal"),
            ("Salud", 10, "2026-13", "Personal"), ("Salud", 10, "2026-1", "Personal"),
            ("Salud", 10, "2026-10", "Ajeno"),
        ):
            with self.subTest(amount=amount, month=month, category=category):
                with self.assertRaises(ValueError):
                    self.store.create_budget(category, amount, month, scope)
        self.assertEqual(self.store.list_budgets("2026-10", "Personal"), {})

    def legacy_database(self, invalid=False):
        # The old layout included movements, settings and category-only budgets.
        self.expense(12345)
        with sqlite3.connect(self.path) as db:
            db.execute("DROP TABLE monthly_budgets")
            db.execute("DELETE FROM settings WHERE key = ?", ("monthly_budgets_v1",))
            db.execute("INSERT INTO budgets VALUES (?, ?)", ("Sueldo" if invalid else "Alimentación", 300000))

    def test_migration_keeps_movements_and_is_idempotent(self):
        self.legacy_database()
        before = self.store.visible()
        month = date.today().strftime("%Y-%m")
        migrated = SQLiteStore(self.path)
        self.assertEqual(migrated.visible(), before)
        self.assertEqual(migrated.list_budgets(month, "Familiar"), {"Alimentación": 300000})
        self.assertEqual(migrated.list_budgets(month, "Personal"), {})
        migrated.delete_budget("Alimentación", month, "Familiar")
        self.assertEqual(SQLiteStore(self.path).list_budgets(month, "Familiar"), {})
        self.assertEqual(SQLiteStore(self.path).visible(), before)

    def test_migration_failure_rolls_back(self):
        self.legacy_database(invalid=True)
        before = self.store.visible()
        with self.assertRaises(StorageError):
            SQLiteStore(self.path)
        with sqlite3.connect(self.path) as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name = 'monthly_budgets'").fetchone())
            self.assertEqual(db.execute("SELECT count(*) FROM budgets").fetchone()[0], 1)
        self.assertEqual(self.store.visible(), before)

    def test_demo_uses_same_rules_without_writing_sqlite(self):
        before = self.path.read_bytes()
        demo = DemoStore()
        demo.create_budget("Salud", 100, "2026-10", "Personal")
        demo.add("Gasto", "Personal", 80, "2026-10-10", "Salud", "Demo")
        self.assertEqual(budget_summary(demo, "2026-10", "Personal")[0]["state"], "warning")
        with self.assertRaises(ValueError):
            demo.create_budget("Salud", 100, "2026-10", "Personal")
        demo.update_budget("Salud", 200, "2026-10", "Personal")
        demo.delete_budget("Salud", "2026-10", "Personal")
        self.assertEqual(demo.list_budgets("2026-10", "Personal"), {})
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)

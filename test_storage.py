"""Pruebas sin Kivy y sin tocar la base personal del usuario."""
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

from nexo.data import DemoStore
from nexo.storage import SQLiteStore, StorageError


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "data" / "nexo.sqlite3"
        self.store = SQLiteStore(self.path)

    def add(self, kind="Ingreso", amount=100000, category="Sueldo", day="2026-11-06"):
        return self.store.add(kind, "Personal", amount, day, category, "Registro de prueba")

    def test_empty_database_and_income(self):
        self.assertEqual(self.store.visible(), [])
        self.assertEqual(self.store.budgets, {})
        movement_id = self.add()
        row = self.store.get(movement_id)
        self.assertEqual(row["amount"], 100000)
        self.assertIs(type(row["amount"]), int)
        self.assertEqual(row["author"], "Usuario local")

    def test_expense_and_balances(self):
        self.add()
        self.add("Gasto", 15000, "Alimentación")
        self.store.add("Ingreso", "Familiar", 80000, "2026-11-06", "Ventas", "Aporte")
        self.assertEqual(self.store.totals("Personal", "2026-11"), (100000, 15000, 85000))
        self.assertEqual(self.store.totals("Familiar", "2026-11"), (80000, 0, 80000))

    def test_reopen_keeps_records_and_settings(self):
        movement_id = self.add()
        original = self.store.get(movement_id)
        self.store.set_home("Mi familia")
        self.store.set_budget("Alimentación", 300000)
        del self.store  # Each operation commits and closes its connection.
        reopened = SQLiteStore(self.path)
        self.assertEqual(reopened.get(movement_id), original)
        self.assertEqual(reopened.home, "Mi familia")
        self.assertEqual(reopened.budgets, {"Alimentación": 300000})
        for _ in range(5):
            self.assertEqual(len(reopened.visible()), 1)

    def test_edit_preserves_id_and_creation(self):
        movement_id = self.add()
        created = self.store.get(movement_id)["registered_at"]
        self.store.update(movement_id, "Gasto", "Personal", 12000, "2026-11-05", "Salud", "Editado")
        row = SQLiteStore(self.path).get(movement_id)
        self.assertEqual(row["registered_at"], created)
        self.assertEqual(row["description"], "Editado")
        self.assertEqual(row["date"], "2026-11-05")
        self.assertEqual(self.store.totals("Personal", "2026-11"), (0, 12000, -12000))

    def test_data_survives_process_exit(self):
        script = """
import sys
from nexo.storage import SQLiteStore
store = SQLiteStore(sys.argv[1])
store.add('Ingreso', 'Personal', 12345, '2026-11-06', 'Sueldo', 'Proceso separado')
"""
        subprocess.run([sys.executable, "-c", script, str(self.path)],
                       cwd=Path(__file__).parent, check=True, capture_output=True, text=True)
        reopened = SQLiteStore(self.path)
        self.assertEqual(reopened.visible()[0]["description"], "Proceso separado")
        self.assertEqual(reopened.totals("Personal", "2026-11"), (12345, 0, 12345))

    def test_delete_is_permanent_and_ids_not_reused(self):
        movement_id = self.add()
        self.store.delete(movement_id)
        self.assertEqual(SQLiteStore(self.path).visible(), [])
        self.assertEqual(self.store.totals("Personal", "2026-11"), (0, 0, 0))
        self.assertGreater(self.add(), movement_id)
        with self.assertRaises(ValueError):
            self.store.delete(movement_id)

    def test_date_time_and_id_order_after_reopen(self):
        with patch("nexo.storage.datetime") as clock:
            clock.now.return_value = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)
            first, second = self.add(), self.add()
            clock.now.return_value = datetime(2026, 11, 6, 11, tzinfo=timezone.utc)
            earlier_time = self.add()
            clock.now.return_value = datetime(2026, 11, 6, 13, tzinfo=timezone.utc)
            earlier_date = self.add(day="2026-11-05")
        self.assertEqual([m["id"] for m in SQLiteStore(self.path).visible()],
                         [second, first, earlier_time, earlier_date])

    def test_demo_does_not_write_local_database(self):
        self.add()
        before = self.path.read_bytes()
        demo = DemoStore()
        demo.add("Ingreso", "Personal", 123, "2026-11-06", "Sueldo", "Solo demo")
        demo.set_home("Demo")
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(SQLiteStore(self.path).visible()), 1)

    def test_validation_and_parameterized_queries(self):
        for kind, amount, day, category, description in (
            ("Ingreso", 0, "2026-11-06", "Sueldo", "Inválido"),
            ("Ingreso", 1.5, "2026-11-06", "Sueldo", "Inválido"),
            ("Ingreso", True, "2026-11-06", "Sueldo", "Inválido"),
            ("Ingreso", 2**63, "2026-11-06", "Sueldo", "Inválido"),
            ("Ingreso", 1, "2026-02-30", "Sueldo", "Inválido"),
            ("Ingreso", 1, "2026-11-06", "Alimentación", "Inválido"),
            ("Gasto", 1, "2026-11-06", "Sueldo", "Inválido"),
            ("Ingreso", 1, "2026-11-06", "Sueldo", "  "),
        ):
            with self.subTest(amount=amount, category=category, day=day):
                with self.assertRaises(ValueError):
                    self.store.add(kind, "Personal", amount, day, category, description)
        self.assertEqual(self.store.visible(), [])
        text = "'); DROP TABLE movements; --"
        movement_id = self.store.add("Ingreso", "Personal", 1, "2026-11-06", "Ventas", text)
        self.assertEqual(self.store.get(movement_id)["description"], text)
        with self.assertRaises(ValueError):
            self.store.update(movement_id, "Gasto", "Personal", 10, "2026-11-06", "Sueldo", "Inválido")
        self.assertEqual(self.store.get(movement_id)["amount"], 1)

    def test_storage_errors_do_not_erase_data(self):
        self.add()
        with patch("nexo.storage.sqlite3.connect", side_effect=sqlite3.OperationalError("locked")):
            with self.assertRaises(StorageError):
                self.store.visible()
            with self.assertRaises(StorageError):
                self.add()
        self.assertEqual(len(SQLiteStore(self.path).visible()), 1)
        corrupt = Path(self.temp.name) / "corrupt.sqlite3"
        corrupt.write_bytes(b"invalid database")
        with self.assertRaises(StorageError):
            SQLiteStore(corrupt)
        self.assertEqual(corrupt.read_bytes(), b"invalid database")


if __name__ == "__main__":
    unittest.main(verbosity=2)

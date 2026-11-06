"""Verificación gráfica y de aislamiento con el Kivy instalado."""
import os
os.environ["KIVY_NO_FILELOG"] = "1"
from datetime import date, datetime, timezone
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.uix.popup import Popup
from nexo.app import NexoFinanzas
from nexo.widgets import Card
from nexo.data import DemoStore, clp, INCOME_CATEGORIES, EXPENSE_CATEGORIES, movement_order


def verify_store():
    store = DemoStore()
    month = date.today().strftime("%Y-%m")
    before = store.totals("Familiar", month)
    store.add("Ingreso", "Personal", 99999, date.today().isoformat(), "Otros ingresos", "Privado ajeno", "Diego")
    assert all(m["description"] != "Privado ajeno" for m in store.visible())
    assert store.totals("Familiar", month) == before
    assert clp(1234567) == "$1.234.567"
    for amount in (0, -1):
        try:
            store.add("Gasto", "Personal", amount, date.today().isoformat(), "Otros egresos", "Inválido")
        except ValueError:
            pass
        else:
            raise AssertionError("Se aceptó monto inválido")
    for kind, category in (("Ingreso", "Alimentación"), ("Gasto", "Sueldo")):
        count = len(store.movements)
        try:
            store.add(kind, "Familiar", 100, date.today().isoformat(), category, "Inválido")
        except ValueError:
            pass
        else:
            raise AssertionError("Se aceptó una categoría de otro tipo")
        assert len(store.movements) == count

    # Controlled clocks cover time precedence, date precedence and exact ties.
    store.movements.clear()
    with patch("nexo.data.datetime") as clock:
        clock.now.return_value = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)
        store.add("Ingreso", "Familiar", 100000, "2026-11-06", "Sueldo", "Primero")
        store.add("Gasto", "Familiar", 20000, "2026-11-06", "Alimentación", "Segundo")
        assert [m["description"] for m in store.visible()] == ["Segundo", "Primero"]
        clock.now.return_value = datetime(2026, 11, 6, 11, tzinfo=timezone.utc)
        store.add("Gasto", "Familiar", 5000, "2026-11-06", "Transporte", "Hora anterior")
        clock.now.return_value = datetime(2026, 11, 6, 13, tzinfo=timezone.utc)
        store.add("Ingreso", "Familiar", 10000, "2026-11-05", "Ventas", "Fecha anterior")
        store.add("Ingreso", "Personal", 777, "2026-11-06", "Bonos", "Privado")
    assert [m["description"] for m in store.visible("Familiar")] == ["Segundo", "Primero", "Hora anterior", "Fecha anterior"]
    assert store.movements == sorted(store.movements, key=movement_order, reverse=True)
    assert len({m["id"] for m in store.movements}) == len(store.movements)
    assert store.totals("Familiar", "2026-11") == (110000, 25000, 85000)
    assert store.totals("Personal", "2026-11") == (777, 0, 777)
    assert store.visible("Familiar", "2026-11", "Alimentación")[0]["description"] == "Segundo"
    print("OK: orden por fecha/hora/ID, categorías, privacidad y resúmenes CLP.")


class VerificationApp(NexoFinanzas):
    failure = None

    def on_start(self):
        self.pages = iter(("Acceso", "Inicio", "Personal", "Registrar", "Historial", "Presupuestos", "Hogar"))
        Clock.schedule_once(self.check_page, .3)

    def check_page(self, _):
        try:
            page = next(self.pages, None)
            if page is None:
                self.check_local_mode()
                print("OK: pantallas demo/local, guardado, edición, borrado y cambio de modo.")
                self.stop()
                return
            self.show(page)
            assert self.manager.current == page
            if page == "Registrar":
                self.check_registration()
            Clock.schedule_once(self.check_page, .15)
        except Exception as exc:
            self.failure = exc
            self.stop()

    def check_registration(self):
        before = self.store.totals("Familiar", self.month)
        for kind, category, amount in (("Ingreso", "Sueldo", 100000), ("Egreso", "Alimentación", 15990)):
            self.show("Registrar")
            save = next(w for w in self.body.children if isinstance(w, Button) and w.text == "Guardar movimiento")
            save.dispatch("on_release")
            assert self.manager.current == "Registrar"
            spinners = [w for w in self.body.children if isinstance(w, Spinner)]
            kind_input = next(w for w in spinners if "Egreso" in w.values)
            category_input = next(w for w in spinners if "Alimentación" in w.values)
            scope = next(w for w in spinners if "Familiar" in w.values)
            assert tuple(category_input.values) == EXPENSE_CATEGORIES
            category_input.text = "Alimentación"
            kind_input.text = "Ingreso"
            assert tuple(category_input.values) == INCOME_CATEGORIES
            assert category_input.text == "Selecciona categoría"
            category_input.text = "Sueldo"
            kind_input.text = "Egreso"
            assert tuple(category_input.values) == EXPENSE_CATEGORIES
            assert category_input.text == "Selecciona categoría"
            kind_input.text = kind
            scope.text = "Familiar"
            for widget in self.body.children:
                if isinstance(widget, TextInput):
                    if widget.hint_text == "Ej.: 15990":
                        widget.text = str(amount)
                    elif widget.hint_text == "Ej.: Compra de supermercado":
                        widget.text = "Prueba " + kind
            # Reject a deliberately injected category from the other kind.
            category_input.text = "Alimentación" if kind == "Ingreso" else "Sueldo"
            count = len(self.store.movements)
            save.dispatch("on_release")
            assert len(self.store.movements) == count
            assert self.manager.current == "Registrar"
            category_input.text = category
            save.dispatch("on_release")
            assert self.manager.current == "Historial"
            assert self.store.visible()[0]["description"] == "Prueba " + kind
            # Results is added last; children are stored in reverse visual order.
            results = self.body.children[0]
            first_card = results.children[-1]
            assert isinstance(first_card, Card)
            assert first_card.children[-1].text.startswith("Prueba " + kind)
        income, expense, balance = before
        assert self.store.totals("Familiar", self.month) == (income + 100000, expense + 15990, balance + 84010)
        self.show("Inicio")
        assert self.store.visible("Familiar", self.month)[0]["description"] == "Prueba Egreso"
        recent_cards = [w for w in reversed(self.body.children) if isinstance(w, Card)]
        assert recent_cards[1].children[-1].text.startswith("Prueba Egreso")

    def check_local_mode(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "local.sqlite3"
            with patch.object(self, "database_path", return_value=path):
                self.enter_mode(True)
                assert self.local_mode
                assert self.store.visible() == []
                self.show("Registrar")
                inputs = self.form_inputs
                inputs["kind"].text = "Ingreso"
                inputs["category"].text = "Sueldo"
                inputs["amount"].text = "70000"
                inputs["description"].text = "Ingreso local de prueba"
                save = next(w for w in self.body.children if isinstance(w, Button) and w.text == "Guardar movimiento")
                save.dispatch("on_release")
                save.dispatch("on_release")  # A repeated release must not duplicate the write.
                assert len(self.store.visible()) == 1
                movement_id = self.store.visible()[0]["id"]
                self.leave_mode()
                self.enter_mode(True)
                assert self.store.get(movement_id)["amount"] == 70000
                self.edit_movement(movement_id)
                assert self.form_inputs["amount"].text == "70000"
                self.form_inputs["amount"].text = "80000"
                save = next(w for w in self.body.children if isinstance(w, Button) and w.text == "Guardar cambios")
                save.dispatch("on_release")
                assert self.store.totals("Personal", self.month) == (80000, 0, 80000)
                for page in ("Inicio", "Personal", "Presupuestos", "Hogar", "Historial"):
                    self.show(page)
                    assert self.manager.current == page
                before = path.read_bytes()
                self.leave_mode()
                self.enter_mode(False)
                self.store.add("Ingreso", "Personal", 123, date.today().isoformat(), "Ventas", "Solo demo")
                assert path.read_bytes() == before
                self.enter_mode(True)
                self.confirm_delete(movement_id)
                popup = next(w for w in Window.children if isinstance(w, Popup))
                remove = next(w for w in popup.content.children if isinstance(w, Button) and w.text == "Eliminar definitivamente")
                remove.dispatch("on_release")
                assert self.store.visible() == []
                assert self.store.totals("Personal", self.month) == (0, 0, 0)
                self.leave_mode()
                self.enter_mode(True)
                assert self.store.visible() == []
                self.leave_mode()


if __name__ == "__main__":
    verify_store()
    app = VerificationApp()
    app.run()
    if app.failure:
        raise app.failure

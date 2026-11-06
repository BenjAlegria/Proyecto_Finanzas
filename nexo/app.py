from datetime import date
from pathlib import Path
from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from nexo.data import DemoStore, CATEGORIES, EXPENSE_CATEGORIES, CATEGORIES_BY_KIND, KIND_LABELS, KIND_VALUES, clp
from nexo.storage import SQLiteStore, StorageError
from nexo.widgets import BG, GREEN, MUTED, Card, label, button, field, select


class NexoFinanzas(App):
    title = "Nexo Finanzas"

    def build(self):
        Window.clearcolor = BG
        if Window.system_size[0] > 600:
            Window.size = (430, 860)
        self.store = DemoStore()
        self.local_mode = False
        self.editing_id = None
        self.month = date.today().strftime("%Y-%m")
        self.manager = ScreenManager(transition=NoTransition())
        self.show("Bienvenida")
        return self.manager

    def show(self, name):
        # Rebuild to keep summaries, budgets and history synchronized.
        self.manager.clear_widgets()
        screen = Screen(name=name)
        shell = BoxLayout(orientation="vertical", padding=[dp(16), dp(12)], spacing=dp(10))
        shell.add_widget(label("N E X O   /   FINANZAS", 16, GREEN, True))
        shell.add_widget(label("LOCAL · Un usuario · Guardado en este dispositivo" if self.local_mode else "DEMO · Datos ficticios · Sin persistencia", 12, MUTED))
        scroll = ScrollView(do_scroll_x=False)
        self.body = BoxLayout(orientation="vertical", spacing=dp(14), size_hint_y=None,
                              padding=[0, dp(8), 0, dp(24)])
        self.body.bind(minimum_height=self.body.setter("height"))
        scroll.add_widget(self.body)
        shell.add_widget(scroll)
        try:
            getattr(self, {"Bienvenida": "welcome", "Acceso": "login", "Inicio": "dashboard",
                       "Personal": "personal", "Registrar": "new_movement", "Historial": "history",
                       "Presupuestos": "budgets", "Hogar": "settings"}[name])()
        except StorageError as exc:
            self.body.clear_widgets()
            self.card("No se pudo cargar esta pantalla", str(exc))
            self.body.add_widget(button("Reintentar", lambda: self.show(name), True))
        if name not in ("Bienvenida", "Acceso"):
            nav = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(4))
            for title in ("Inicio", "Personal", "Registrar", "Historial", "Hogar"):
                nav.add_widget(button("+ Nuevo" if title == "Registrar" else title,
                                      lambda target=title: self.navigate(target), name == title))
            shell.add_widget(nav)
        screen.add_widget(shell)
        self.manager.add_widget(screen)
        self.manager.current = name

    def navigate(self, target):
        self.editing_id = None
        self.show(target)

    def database_path(self):
        return Path(self.user_data_dir) / "nexo.sqlite3"

    def enter_mode(self, local):
        try:
            store = SQLiteStore(self.database_path()) if local else DemoStore()
            # Check reads before switching away from the mode selection.
            store.visible()
        except StorageError as exc:
            self.message("Almacenamiento local", str(exc))
            return
        self.store = store
        self.local_mode = local
        self.editing_id = None
        self.history_month = self.month
        self.show("Inicio")

    def leave_mode(self):
        self.store = DemoStore()
        self.local_mode = False
        self.editing_id = None
        self.show("Acceso")

    def message(self, title, text):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(label(text))
        popup = Popup(title=title, content=content, size_hint=(.9, .6))
        content.add_widget(button("Cerrar", popup.dismiss, True))
        popup.open()

    def heading(self, title, subtitle):
        self.body.add_widget(label(title, 28, bold=True))
        self.body.add_widget(label(subtitle, 14, MUTED))

    def card(self, *texts):
        card = Card()
        for text in texts:
            card.add_widget(label(text))
        self.body.add_widget(card)
        return card

    def welcome(self):
        self.heading("Tu hogar, en equilibrio.", "Un espacio para organizar lo que comparten y cuidar lo que es tuyo.")
        self.card("01   Una visión familiar", "Ingresos, egresos y presupuesto en un solo lugar.")
        self.card("02   Tu espacio privado", "Tus movimientos personales no se suman al hogar.")
        self.card("03   Decisiones con claridad", "Montos en pesos chilenos, sin decimales.")
        self.body.add_widget(button("Comenzar", lambda: self.show("Acceso"), True))

    def login(self):
        self.heading("Elige cómo comenzar", "Demostración y datos locales separados.")
        self.card("Modo personal local", "Comienza sin movimientos o recupera los ya guardados en este dispositivo. Sin cuenta ni autenticación.")
        self.body.add_widget(button("Abrir modo personal local", lambda: self.enter_mode(True), True))
        self.card("Sesión de demostración", "Camila Rivera · Administradora", "No ingreses correo ni contraseña reales. El acceso no verifica una identidad.")
        self.body.add_widget(button("Iniciar sesión demo", lambda: self.enter_mode(False)))
        self.body.add_widget(button("Volver", lambda: self.show("Bienvenida")))

    def summary(self, scope):
        income, expense, balance = self.store.totals(scope, self.month)
        card = Card()
        card.add_widget(label("SALDO MENSUAL · CLP", 13, MUTED))
        card.add_widget(label(clp(balance), 34, GREEN, True))
        card.add_widget(label(f"Ingresos   {clp(income)}\nEgresos    {clp(expense)}", 17))
        self.body.add_widget(card)

    def dashboard(self):
        self.heading(self.store.home, f"{'Resumen local' if self.local_mode else 'Hola, Camila'} · Mes {self.month}")
        self.summary("Familiar")
        self.body.add_widget(button("Ver presupuestos mensuales", lambda: self.show("Presupuestos")))
        self.body.add_widget(label("Últimos movimientos familiares", 19, bold=True))
        self.rows(self.body, self.store.visible("Familiar", self.month)[:4])

    def personal(self):
        self.heading("Mis finanzas", "Ámbito personal · Datos de este dispositivo." if self.local_mode else "Privado · Solo visible para Camila en esta demo.")
        self.summary("Personal")
        if self.local_mode:
            self.card("Uso local de un solo usuario", "Personal y Familiar organizan tus registros. No hay autenticación, permisos entre integrantes ni sincronización. La base no está cifrada.")
        else:
            self.card("Tu privacidad primero", "El administrador del hogar no puede acceder a movimientos personales ajenos. Los ingresos personales no aportan automáticamente al hogar.")
        self.rows(self.body, self.store.visible("Personal", self.month))

    def rows(self, container, movements):
        if not movements:
            container.add_widget(label("Sin movimientos para estos filtros.", color=MUTED))
        for m in movements:
            card = Card()
            sign = "+" if m["kind"] == "Ingreso" else "−"
            card.add_widget(label(f'{m["description"]}   {sign}{clp(m["amount"])}', 16, bold=True))
            card.add_widget(label(f'{m["date"]} · {KIND_LABELS[m["kind"]]} · {m["category"]}\n{m["scope"]} · {m["author"]}', 13, MUTED))
            if self.local_mode:
                actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
                actions.add_widget(button("Editar", lambda movement_id=m["id"]: self.edit_movement(movement_id)))
                actions.add_widget(button("Eliminar", lambda movement_id=m["id"]: self.confirm_delete(movement_id)))
                card.add_widget(actions)
            container.add_widget(card)

    def edit_movement(self, movement_id):
        try:
            self.store.get(movement_id)
        except (StorageError, ValueError) as exc:
            self.message("No se pudo abrir el movimiento", str(exc))
            return
        self.editing_id = movement_id
        self.show("Registrar")

    def confirm_delete(self, movement_id):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(label("¿Eliminar este movimiento? Se actualizarán los saldos. Esta acción no se puede deshacer."))
        popup = Popup(title="Eliminar movimiento", content=content, size_hint=(.9, .65))

        def remove():
            try:
                self.store.delete(movement_id)
            except (StorageError, ValueError) as exc:
                self.message("No se pudo eliminar", str(exc))
                return
            popup.dismiss()
            self.show("Historial")

        content.add_widget(button("Eliminar definitivamente", remove, True))
        content.add_widget(button("Cancelar", popup.dismiss))
        popup.open()

    def new_movement(self):
        editing_id = self.editing_id if self.local_mode else None
        existing = self.store.get(editing_id) if editing_id is not None else None
        self.heading("Editar movimiento" if existing else "Nuevo movimiento", "Registra un ingreso o egreso en CLP.")
        inputs = {}
        for key, title, widget in (
            ("kind", "Tipo", select(("Egreso", "Ingreso"))),
            ("scope", "Visibilidad", select(("Personal", "Familiar"))),
            ("amount", "Monto CLP · entero sin separadores", field("Ej.: 15990")),
            ("date", "Fecha · AAAA-MM-DD", field("Fecha", date.today().isoformat())),
            ("category", "Categoría", select(CATEGORIES_BY_KIND["Gasto"], "Selecciona categoría")),
            ("description", "Descripción", field("Ej.: Compra de supermercado")),
        ):
            self.body.add_widget(label(title, 13, MUTED))
            self.body.add_widget(widget)
            inputs[key] = widget
        def update_categories(_, value):
            category = inputs["category"]
            category.values = CATEGORIES_BY_KIND[KIND_VALUES[value]]
            if category.text not in category.values:
                category.text = "Selecciona categoría"

        inputs["kind"].bind(text=update_categories)
        privacy = label("", 13, GREEN)
        def scope_hint(_, value):
            privacy.text = "Ámbito organizativo local; sin permisos multiusuario." if self.local_mode else ("Personal: solo tú puedes verlo." if value == "Personal" else "Familiar: compartido con los integrantes autorizados.")
        inputs["scope"].bind(text=scope_hint)
        scope_hint(None, inputs["scope"].text)
        if existing:
            inputs["kind"].text = KIND_LABELS[existing["kind"]]
            for key in ("scope", "amount", "category", "description"):
                inputs[key].text = str(existing[key])
            inputs["date"].text = existing["date"]
        self.form_inputs = inputs
        self.body.add_widget(privacy)
        status = label("", 14)
        self.body.add_widget(status)
        saved = False

        def save():
            nonlocal saved
            if saved:
                return
            try:
                values = {key: widget.text for key, widget in inputs.items()}
                values["kind"] = KIND_VALUES[values["kind"]]
                values["amount"] = int(values["amount"])
                args = (values["kind"], values["scope"], values["amount"], values["date"], values["category"], values["description"])
                if editing_id is None:
                    self.store.add(*args)
                else:
                    self.store.update(editing_id, *args)
            except StorageError as exc:
                status.text = str(exc)
                return
            except ValueError as exc:
                status.text = "Revisa monto entero positivo y fecha AAAA-MM-DD. " + str(exc)
                return
            saved = True
            self.editing_id = None
            self.history_month = values["date"][:7]
            self.show("Historial")

        self.body.add_widget(button("Guardar cambios" if existing else "Guardar movimiento", save, True))
        if existing:
            def cancel():
                self.editing_id = None
                self.show("Historial")
            self.body.add_widget(button("Cancelar edición", cancel))

    def history(self):
        self.heading("Historial", "Registros locales · Un solo usuario." if self.local_mode else "Movimientos compartidos y tus movimientos privados.")
        month = field("Mes AAAA-MM", getattr(self, "history_month", self.month))
        scope = select(("Todos los ámbitos", "Familiar", "Personal"))
        category = select(("Todas las categorías",) + CATEGORIES)
        for widget in (month, scope, category):
            self.body.add_widget(widget)
        status = label("", 13, MUTED)
        results = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        results.bind(minimum_height=results.setter("height"))

        def refresh(*_):
            results.clear_widgets()
            try:
                parsed = date.fromisoformat(month.text + "-01")
                if parsed.strftime("%Y-%m") != month.text:
                    raise ValueError()
            except ValueError:
                status.text = "Escribe un mes válido: AAAA-MM."
                return
            status.text = "Datos locales de este dispositivo." if self.local_mode else "Solo movimientos autorizados para Camila (simulación)."
            try:
                self.rows(results, self.store.visible(None if scope.text.startswith("Todos") else scope.text,
                          month.text, None if category.text.startswith("Todas") else category.text))
            except StorageError as exc:
                status.text = str(exc)

        self.body.add_widget(button("Aplicar filtros", refresh, True))
        self.body.add_widget(status)
        self.body.add_widget(results)
        refresh()

    def budgets(self):
        self.heading("Presupuestos", f"Límites familiares · {self.month} · CLP")
        for category, limit in self.store.budgets.items():
            spent = sum(m["amount"] for m in self.store.visible("Familiar", self.month, category) if m["kind"] == "Gasto")
            card = Card()
            card.add_widget(label(category, 19, bold=True))
            card.add_widget(label(f"{clp(spent)} de {clp(limit)} · {spent / limit:.0%}"))
            card.add_widget(ProgressBar(max=limit, value=min(spent, limit), size_hint_y=None, height=dp(14)))
            card.add_widget(label("Límite superado" if spent > limit else f"Disponible: {clp(limit - spent)}", color=GREEN if spent <= limit else (1, .55, .4, 1)))
            self.body.add_widget(card)
        category_input = select(EXPENSE_CATEGORIES if self.local_mode else tuple(self.store.budgets))
        amount = field("Nuevo límite mensual CLP")
        status = label("", 13)
        self.body.add_widget(label("Configurar límite local" if self.local_mode else "Editar límite · Administradora", 17, bold=True))
        for widget in (category_input, amount, status):
            self.body.add_widget(widget)

        def save():
            try:
                value = int(amount.text)
                if value <= 0:
                    raise ValueError()
                self.store.set_budget(category_input.text, value)
            except StorageError as exc:
                status.text = str(exc)
                return
            except ValueError:
                status.text = "Usa un monto entero mayor que cero."
                return
            self.show("Presupuestos")

        self.body.add_widget(button("Actualizar límite", save, True))
        self.body.add_widget(button("Volver al inicio", lambda: self.show("Inicio")))

    def settings(self):
        self.heading("Hogar y ajustes", "Un espacio compartido, con límites claros.")
        home = field("Nombre del hogar", self.store.home)
        self.body.add_widget(label("Nombre del hogar", 14, MUTED))
        self.body.add_widget(home)
        status = label("", 13, GREEN)

        def save():
            if not home.text.strip():
                status.text = "Escribe un nombre para el hogar."
                return
            try:
                self.store.set_home(home.text)
            except (StorageError, ValueError) as exc:
                status.text = str(exc)
                return
            status.text = "Nombre guardado en el dispositivo." if self.local_mode else "Nombre actualizado para esta sesión."

        self.body.add_widget(button("Guardar nombre", save, True))
        self.body.add_widget(status)
        if self.local_mode:
            self.card("Modo local · Un usuario", "Sin cuentas autenticadas ni integrantes compartidos. Los permisos familiares se implementarán en un backend futuro.", "Base SQLite sin cifrar, guardada en:", str(self.database_path()))
        else:
            self.card("Integrantes ficticios", "Camila Rivera · Administradora", "Diego Rivera · Integrante autorizado", "Ambos ven los movimientos familiares. Los personales pertenecen solo a su autor.")
        self.card("Preferencias", "Moneda: CLP · Tema: oscuro", "Invitaciones y cambios de permisos pendientes de un servicio autenticado. No se envían invitaciones desde esta demo.")
        self.body.add_widget(button("Presupuestos del hogar", lambda: self.show("Presupuestos")))
        self.body.add_widget(button("Cambiar de modo" if self.local_mode else "Cerrar sesión demo", self.leave_mode))

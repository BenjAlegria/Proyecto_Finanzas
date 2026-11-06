from datetime import date
from pathlib import Path
from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from nexo.design import theme
from nexo.settings_widgets import RoundedField, RoundedButton, RoundedSelect, SettingsHeader, OptionCard, settings_panel, feedback
from kivy.uix.screenmanager import ScreenManager, NoTransition
from nexo.data import DemoStore, KIND_LABELS, KIND_VALUES, clp
from nexo.storage import SQLiteStore, StorageError
from nexo.budgets import budget_summary, validate_month
from nexo.category_ui import categories_screen
from nexo.widgets import PRIMARY, MUTED, Card, Popup, ProgressBar, ThemedScreen, label, button, field, select, heading, indicator, navigation


class NexoFinanzas(App):
    title = "Nexo Finanzas"
    categories = categories_screen

    def build(self):
        theme.load(Path(self.user_data_dir) / "appearance.json")
        theme.track(Window, clearcolor="bg")
        self.theme_timer = Clock.schedule_interval(theme.refresh, 2)
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
        screen = ThemedScreen(name=name)
        shell = BoxLayout(orientation="vertical", padding=[dp(18), dp(10)], spacing=dp(8))
        brand = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
        brand.add_widget(label("Nexo Finanzas", 19, PRIMARY, True))
        shell.add_widget(brand)
        if name != "Hogar":
            shell.add_widget(label("Tu dinero, en equilibrio.", 12, MUTED))
        shell.add_widget(label("LOCAL · Un usuario · Datos en este dispositivo" if self.local_mode else "DEMO · Datos ficticios · Sin persistencia", 11, MUTED))
        scroll = ScrollView(do_scroll_x=False)
        self.body = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None,
                              padding=[0, dp(8), 0, dp(24)])
        self.body.bind(minimum_height=self.body.setter("height"))
        scroll.add_widget(self.body)
        shell.add_widget(scroll)
        try:
            getattr(self, {"Bienvenida": "welcome", "Acceso": "login", "Inicio": "dashboard",
                       "Personal": "personal", "Registrar": "new_movement", "Historial": "history",
                       "Presupuestos": "budgets", "Hogar": "settings", "Categorías": "categories"}[name])()
        except StorageError as exc:
            self.body.clear_widgets()
            self.card("No se pudo cargar esta pantalla", str(exc))
            self.body.add_widget(button("Reintentar", lambda: self.show(name), True))
        if name not in ("Bienvenida", "Acceso"):
            shell.add_widget(navigation(name, self.navigate))
        screen.add_widget(shell)
        self.manager.add_widget(screen)
        self.manager.current = name

    def change_theme(self, value):
        try:
            theme.set(value)
        except OSError as exc:
            self.message("Preferencia de apariencia", str(exc))

    def on_stop(self):
        if hasattr(self, "theme_timer"):
            self.theme_timer.cancel()

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
        self.budget_month, self.budget_scope = self.month, "Familiar"
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
        self.body.add_widget(heading(title, subtitle))

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
        card.add_widget(label(clp(balance), 34, PRIMARY, True))
        stats = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(12))
        stats.add_widget(indicator("INGRESOS", clp(income), "income"))
        stats.add_widget(indicator("EGRESOS", clp(expense), "expense"))
        card.add_widget(stats)
        self.body.add_widget(card)

    def dashboard(self):
        self.heading(self.store.home, f"Resumen familiar · {self.month}")
        self.summary("Familiar")
        self.body.add_widget(button("Ver presupuestos mensuales", lambda: self.show("Presupuestos")))
        self.body.add_widget(label("Actividad reciente", 18, bold=True))
        self.rows(self.body, self.store.visible("Familiar", self.month)[:4])

    def personal(self):
        self.heading("Mis finanzas", "Ámbito personal · Datos de este dispositivo." if self.local_mode else "Privado · Solo visible para Camila en esta demo.")
        self.summary("Personal")
        if self.local_mode:
            self.body.add_widget(label("Un usuario local · Sin permisos multiusuario ni cifrado.", 12, MUTED))
        else:
            self.card("Tu privacidad primero", "El administrador del hogar no puede acceder a movimientos personales ajenos. Los ingresos personales no aportan automáticamente al hogar.")
        self.rows(self.body, self.store.visible("Personal", self.month))

    def rows(self, container, movements):
        if not movements:
            container.add_widget(label("Sin movimientos para estos filtros.", color=MUTED))
        for m in movements:
            card = Card()
            sign = "+" if m["kind"] == "Ingreso" else "−"
            card.add_widget(label(f'{m["description"]}   {sign}{clp(m["amount"])}', 16,
                                  "income" if m["kind"] == "Ingreso" else "expense", bold=True))
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
            ("scope", "Ámbito del movimiento", select(("Personal", "Familiar"))),
            ("amount", "Monto CLP · entero sin separadores", field("Ej.: 15990")),
            ("date", "Fecha · AAAA-MM-DD", field("Fecha", date.today().isoformat())),
            ("category", "Categoría", select(self.store.category_names("Gasto", "Personal"), "Selecciona categoría")),
            ("description", "Descripción", field("Ej.: Compra de supermercado")),
        ):
            self.body.add_widget(label(title, 13, MUTED))
            self.body.add_widget(widget)
            inputs[key] = widget
        def update_categories(_, value):
            category = inputs["category"]
            kind, scope = KIND_VALUES[inputs["kind"].text], inputs["scope"].text
            options = self.store.category_names(kind, scope)
            if existing and (existing["kind"], existing["scope"]) == (kind, scope) and existing["category"] not in options:
                options += (existing["category"],)
            category.values = options
            if category.text not in category.values:
                category.text = "Selecciona categoría"

        inputs["kind"].bind(text=update_categories)
        inputs["scope"].bind(text=update_categories)
        privacy = label("", 13, PRIMARY)
        def scope_hint(_, value):
            privacy.text = "Ámbito organizativo local; sin permisos multiusuario." if self.local_mode else ("Personal: solo tú puedes verlo." if value == "Personal" else "Familiar: compartido con los integrantes autorizados.")
        inputs["scope"].bind(text=scope_hint)
        scope_hint(None, inputs["scope"].text)
        if existing:
            inputs["kind"].text = KIND_LABELS[existing["kind"]]
            for key in ("scope", "amount", "category", "description"):
                inputs[key].text = str(existing[key])
            inputs["date"].text = existing["date"]
            update_categories(None, None)
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
        names = {row["name"] for row in self.store.list_categories(active_only=False)}
        names.update(m["category"] for m in self.store.visible())
        category = select(("Todas las categorías",) + tuple(sorted(names)))
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
        self.heading("Presupuestos", "Límites mensuales por categoría · CLP")
        month = field("Mes AAAA-MM", getattr(self, "budget_month", self.month))
        scope = select(("Familiar", "Personal"), getattr(self, "budget_scope", "Familiar"))
        self.body.add_widget(label("Mes a consultar o configurar · AAAA-MM", 13, MUTED))
        self.body.add_widget(month)
        self.body.add_widget(scope)
        self.body.add_widget(label("Ámbitos organizativos locales, sin permisos multiusuario." if self.local_mode else "DEMO · Presupuestos ficticios en memoria.", 13, MUTED))
        status = label("", 13)

        def apply_filters():
            try:
                validate_month(month.text)
            except ValueError as exc:
                status.text = str(exc)
                return
            self.budget_month, self.budget_scope = month.text, scope.text
            self.show("Presupuestos")

        self.body.add_widget(button("Consultar mes y ámbito", apply_filters, True))
        self.body.add_widget(status)
        selected_month, selected_scope = month.text, scope.text
        summaries = budget_summary(self.store, selected_month, selected_scope)
        if not summaries:
            self.body.add_widget(label("Sin presupuestos para este mes y ámbito.", color=MUTED))
        for summary in summaries:
            category, limit, used = summary["category"], summary["amount"], summary["used"]
            state = summary["state"]
            color = "expense" if state in ("exceeded", "reached") else ("warning" if state == "warning" else PRIMARY)
            card = Card()
            card.add_widget(label(category, 19, bold=True))
            card.add_widget(label(f"{selected_month} · {selected_scope}", 13, MUTED))
            card.add_widget(label(f"Utilizado: {clp(used)} de {clp(limit)} · {summary['percent']:.1f}%"))
            card.add_widget(ProgressBar(max=limit, value=min(used, limit), size_hint_y=None, height=dp(14)))
            card.add_widget(label(f"Disponible: {clp(summary['remaining'])}", color=color))
            warning = {"exceeded": "Presupuesto superado: más del 100%.",
                       "reached": "Límite alcanzado: 100% del presupuesto.",
                       "warning": "Atención: utilizaste al menos el 80% del presupuesto.",
                       "normal": "Dentro del presupuesto."}[state]
            card.add_widget(label(warning, color=color))
            actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
            actions.add_widget(button("Editar límite", lambda c=category, v=limit: self.edit_budget(c, v, selected_month, selected_scope)))
            actions.add_widget(button("Eliminar", lambda c=category: self.delete_budget(c, selected_month, selected_scope)))
            card.add_widget(actions)
            self.body.add_widget(card)
        self.body.add_widget(label("Crear presupuesto", 19, bold=True))
        self.body.add_widget(label(f"Para {selected_month} · {selected_scope}. Aplica los filtros para cambiar el destino.", 13, MUTED))
        available = self.store.category_names("Gasto", selected_scope)
        category_input = select(available, available[0] if available else "Sin categorías activas")
        amount = field("Monto máximo CLP sin separadores")
        for widget in (category_input, amount):
            self.body.add_widget(widget)

        def create():
            try:
                self.store.create_budget(category_input.text, int(amount.text), selected_month, selected_scope)
            except (ValueError, StorageError) as exc:
                status.text = "No se pudo crear. " + str(exc)
                return
            self.show("Presupuestos")

        self.body.add_widget(button("Crear presupuesto", create, True))
        self.body.add_widget(button("Volver al inicio", lambda: self.show("Inicio")))

    def edit_budget(self, category, current, month, scope):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        content.add_widget(label(f"{category} · {month} · {scope}"))
        amount = field("Monto máximo CLP", str(current))
        content.add_widget(amount)
        status = label("", 13)
        content.add_widget(status)
        popup = Popup(title="Editar presupuesto", content=content, size_hint=(.9, .75))

        def save():
            try:
                self.store.update_budget(category, int(amount.text), month, scope)
            except (ValueError, StorageError) as exc:
                status.text = "No se pudo guardar. " + str(exc)
                return
            popup.dismiss()
            self.show("Presupuestos")

        content.add_widget(button("Guardar límite", save, True))
        content.add_widget(button("Cancelar", popup.dismiss))
        popup.open()

    def delete_budget(self, category, month, scope):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        content.add_widget(label(f"¿Eliminar el presupuesto de {category}, {month}, {scope}? Los movimientos se conservarán."))
        status = label("", 13)
        content.add_widget(status)
        popup = Popup(title="Eliminar presupuesto", content=content, size_hint=(.9, .7))

        def remove():
            try:
                self.store.delete_budget(category, month, scope)
            except (ValueError, StorageError) as exc:
                status.text = str(exc)
                return
            popup.dismiss()
            self.show("Presupuestos")

        content.add_widget(button("Eliminar presupuesto", remove, True))
        content.add_widget(button("Cancelar", popup.dismiss))
        popup.open()

    def settings(self):
        self.body.spacing = dp(12)
        self.heading("Hogar y ajustes", "Un espacio para organizar tu hogar y tus preferencias.")
        home_card = settings_panel("Mi hogar", "Nombre y configuración básica", "home")
        home_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        home = RoundedField("Nombre del hogar", self.store.home)
        status = feedback()

        def save():
            if status.parent is None:
                home_card.add_widget(status)
            try:
                self.store.set_home(home.text)
            except (StorageError, ValueError) as exc:
                status.text = str(exc)
                return
            status.text = "Nombre guardado en el dispositivo." if self.local_mode else "Nombre actualizado para esta sesión."

        home_row.add_widget(home)
        save_button = RoundedButton("Guardar", save, True)
        save_button.size_hint_x, save_button.width = None, dp(88)
        home_row.add_widget(save_button)
        home_card.add_widget(home_row)
        self.body.add_widget(home_card)
        self.body.add_widget(OptionCard("Categorías", "Organiza tus ingresos y egresos", "categories", lambda: self.show("Categorías")))
        appearance_card = Card()
        appearance = RoundedSelect(theme.options, theme.preference if theme.preference in theme.options else "Claro")
        appearance.size_hint_x, appearance.width = None, dp(110)
        appearance_header = SettingsHeader("Apariencia", "Tema " + appearance.text.lower(), "appearance", appearance)
        def change_appearance(_, value):
            self.change_theme(value)
            appearance_header.description.text = "Tema " + theme.preference.lower()
        appearance.bind(text=change_appearance)
        appearance_card.add_widget(appearance_header)
        self.body.add_widget(appearance_card)
        self.body.add_widget(OptionCard("Privacidad y datos", "Almacenamiento local y seguridad", "privacy", self.privacy_details))
        self.body.add_widget(RoundedButton("Presupuestos del hogar", lambda: self.show("Presupuestos")))
        self.body.add_widget(RoundedButton("Cambiar de modo" if self.local_mode else "Cerrar sesión demo", self.leave_mode))

    def privacy_details(self):
        if self.local_mode:
            self.message("Privacidad y datos", "Modo local · Un solo usuario.\nSQLite sin cifrar; sin permisos entre integrantes ni sincronización.\nBase guardada en:\n" + str(self.database_path()) + "\nMoneda: CLP. Invitaciones pendientes de un servicio autenticado.")
        else:
            self.message("Privacidad y datos", "DEMO · Datos ficticios en memoria, sin persistencia.\nCamila Rivera · Administradora ficticia.\nDiego Rivera · Integrante ficticio.\nLa separación de movimientos personales y familiares es una simulación. No hay autenticación real.\nMoneda: CLP. No se envían invitaciones.")



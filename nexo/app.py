from datetime import date
from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from nexo.data import DemoStore, CATEGORIES, CATEGORIES_BY_KIND, KIND_LABELS, KIND_VALUES, clp
from nexo.widgets import BG, GREEN, MUTED, Card, label, button, field, select


class NexoFinanzas(App):
    title = "Nexo Finanzas · Demo"

    def build(self):
        Window.clearcolor = BG
        if Window.system_size[0] > 600:
            Window.size = (430, 860)
        self.store = DemoStore()
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
        shell.add_widget(label("DEMO · Datos ficticios · Sin persistencia", 12, MUTED))
        scroll = ScrollView(do_scroll_x=False)
        self.body = BoxLayout(orientation="vertical", spacing=dp(14), size_hint_y=None,
                              padding=[0, dp(8), 0, dp(24)])
        self.body.bind(minimum_height=self.body.setter("height"))
        scroll.add_widget(self.body)
        shell.add_widget(scroll)
        getattr(self, {"Bienvenida": "welcome", "Acceso": "login", "Inicio": "dashboard",
                       "Personal": "personal", "Registrar": "new_movement", "Historial": "history",
                       "Presupuestos": "budgets", "Hogar": "settings"}[name])()
        if name not in ("Bienvenida", "Acceso"):
            nav = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(4))
            for title in ("Inicio", "Personal", "Registrar", "Historial", "Hogar"):
                nav.add_widget(button("+ Nuevo" if title == "Registrar" else title,
                                      lambda target=title: self.show(target), name == title))
            shell.add_widget(nav)
        screen.add_widget(shell)
        self.manager.add_widget(screen)
        self.manager.current = name

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
        self.heading("Bienvenida, Camila", "Explora el prototipo con una identidad ficticia.")
        self.card("Sesión de demostración", "Camila Rivera · Administradora", "No ingreses correo ni contraseña reales. El acceso no verifica una identidad.")
        self.body.add_widget(button("Iniciar sesión demo", lambda: self.show("Inicio"), True))
        self.body.add_widget(button("Volver", lambda: self.show("Bienvenida")))

    def summary(self, scope):
        income, expense, balance = self.store.totals(scope, self.month)
        card = Card()
        card.add_widget(label("SALDO MENSUAL · CLP", 13, MUTED))
        card.add_widget(label(clp(balance), 34, GREEN, True))
        card.add_widget(label(f"Ingresos   {clp(income)}\nEgresos    {clp(expense)}", 17))
        self.body.add_widget(card)

    def dashboard(self):
        self.heading(self.store.home, f"Hola, Camila · Mes {self.month}")
        self.summary("Familiar")
        self.body.add_widget(button("Ver presupuestos mensuales", lambda: self.show("Presupuestos")))
        self.body.add_widget(label("Últimos movimientos familiares", 19, bold=True))
        self.rows(self.body, self.store.visible("Familiar", self.month)[:4])

    def personal(self):
        self.heading("Mis finanzas", "Privado · Solo visible para Camila en esta demo.")
        self.summary("Personal")
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
            container.add_widget(card)

    def new_movement(self):
        self.heading("Nuevo movimiento", "Registra un ingreso o egreso en CLP.")
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
        privacy = label("Personal: solo tú puedes verlo.", 13, GREEN)
        inputs["scope"].bind(text=lambda _, value: setattr(privacy, "text", "Personal: solo tú puedes verlo." if value == "Personal" else "Familiar: compartido con los integrantes autorizados."))
        self.body.add_widget(privacy)
        status = label("", 14)
        self.body.add_widget(status)

        def save():
            try:
                values = {key: widget.text for key, widget in inputs.items()}
                values["kind"] = KIND_VALUES[values["kind"]]
                values["amount"] = int(values["amount"])
                self.store.add(values["kind"], values["scope"], values["amount"], values["date"], values["category"], values["description"])
            except ValueError:
                status.text = "Revisa monto entero positivo, fecha válida (AAAA-MM-DD), categoría del tipo seleccionado y descripción."
                return
            self.show("Historial")

        self.body.add_widget(button("Guardar movimiento", save, True))

    def history(self):
        self.heading("Historial", "Movimientos compartidos y tus movimientos privados.")
        month = field("Mes AAAA-MM", self.month)
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
            status.text = "Solo movimientos autorizados para Camila (simulación)."
            self.rows(results, self.store.visible(None if scope.text.startswith("Todos") else scope.text,
                      month.text, None if category.text.startswith("Todas") else category.text))

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
        category_input = select(tuple(self.store.budgets))
        amount = field("Nuevo límite mensual CLP")
        status = label("", 13)
        self.body.add_widget(label("Editar límite · Administradora", 17, bold=True))
        for widget in (category_input, amount, status):
            self.body.add_widget(widget)

        def save():
            try:
                value = int(amount.text)
                if value <= 0:
                    raise ValueError()
            except ValueError:
                status.text = "Usa un monto entero mayor que cero."
                return
            self.store.budgets[category_input.text] = value
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
            self.store.home = home.text.strip()
            status.text = "Nombre actualizado para esta sesión."

        self.body.add_widget(button("Guardar nombre", save, True))
        self.body.add_widget(status)
        self.card("Integrantes ficticios", "Camila Rivera · Administradora", "Diego Rivera · Integrante autorizado", "Ambos ven los movimientos familiares. Los personales pertenecen solo a su autor.")
        self.card("Preferencias", "Moneda: CLP · Tema: oscuro", "Invitaciones y cambios de permisos pendientes de un servicio autenticado. No se envían invitaciones desde esta demo.")
        self.body.add_widget(button("Presupuestos del hogar", lambda: self.show("Presupuestos")))
        self.body.add_widget(button("Cerrar sesión demo", lambda: self.show("Acceso")))

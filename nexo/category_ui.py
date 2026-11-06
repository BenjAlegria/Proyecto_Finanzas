"""Administración compacta del catálogo usando los componentes existentes."""
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from nexo.widgets import Card, Popup, label, field, button, segmented, MUTED
from nexo.data import KIND_VALUES, KIND_LABELS
from nexo.storage import StorageError


def categories_screen(app):
    app.heading("Mis categorías", "Organiza tus ingresos y egresos creando categorías adaptadas a tus necesidades")
    app.body.add_widget(label("Agrupa tus movimientos para entender en qué recibes y utilizas tu dinero.", 12, MUTED))
    kind = getattr(app, "category_kind", "Egreso")
    scope = getattr(app, "category_scope", "Personal")

    def change_kind(value):
        new_kind = "Ingreso" if value == "Ingresos" else "Egreso"
        if new_kind == kind:
            return
        app.category_kind, app.category_scope = new_kind, scope
        app.show("Categorías")

    def change_scope(value):
        if value == scope:
            return
        app.category_kind, app.category_scope = kind, value
        app.show("Categorías")

    app.body.add_widget(segmented(("Ingresos", "Egresos"), "Ingresos" if kind == "Ingreso" else "Egresos", change_kind))
    app.body.add_widget(segmented(("Personal", "Familiar"), scope, change_scope))
    app.body.add_widget(label("Personal organiza tus finanzas; Familiar, las del hogar. Son ámbitos locales, sin usuarios autenticados.", 12, MUTED))
    selected_kind, selected_scope = KIND_VALUES[kind], scope
    form = Card()
    form.add_widget(label("Nueva categoría", 17, bold=True))
    form.add_widget(label(f"{kind} · {scope}", 12, MUTED))
    name = field("Ej. Mascotas")
    status = label(getattr(app, "category_notice", ""), 13)
    app.category_notice = ""
    form.add_widget(name)

    def create():
        try:
            app.store.create_category(name.text, selected_kind, selected_scope)
        except (ValueError, StorageError) as exc:
            status.text = str(exc)
            return
        app.category_notice = "Categoría creada. Ya está disponible en los formularios."
        app.show("Categorías")

    form.add_widget(button("Agregar categoría", create, True))
    # Feedback collapses when empty; the field and action stay adjacent.
    def feedback_size(*_):
        status.height = max(dp(22), status.texture_size[1] + dp(4)) if status.text else 0
    status.bind(text=feedback_size, texture_size=feedback_size)
    feedback_size()
    form.add_widget(status)
    app.body.add_widget(form)
    app.body.add_widget(label(f"Categorías de {'ingreso' if kind == 'Ingreso' else 'egreso'} — {scope}", 18, bold=True))

    def edit(row, deactivate=False, activate=False):
        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        content.add_widget(label(f'{row["name"]} · {KIND_LABELS[row["kind"]]} · {row["scope"]}'))
        entry = field("Nuevo nombre", row["name"])
        if activate:
            content.add_widget(label("La categoría volverá a estar disponible para nuevos movimientos. El historial y los presupuestos se conservarán."))
        elif deactivate:
            content.add_widget(label("Dejará de estar disponible para nuevos registros. El historial se conserva. Si tiene presupuestos vinculados, el cambio se bloqueará."))
        else:
            content.add_widget(entry)
            content.add_widget(label("El historial conserva el nombre usado al registrar cada movimiento.", 13, MUTED))
        message = label("", 13)
        content.add_widget(message)
        popup = Popup(title="Activar categoría" if activate else "Desactivar categoría" if deactivate else "Editar categoría", content=content, size_hint=(.9, .8))

        def confirm():
            try:
                if activate:
                    app.store.activate_category(row["id"])
                elif deactivate:
                    app.store.deactivate_category(row["id"])
                else:
                    app.store.rename_category(row["id"], entry.text)
            except (ValueError, StorageError) as exc:
                message.text = str(exc)
                return
            popup.dismiss()
            app.category_notice = "Categoría activada." if activate else "Categoría desactivada." if deactivate else "Nombre actualizado."
            app.show("Categorías")

        content.add_widget(button("Confirmar activación" if activate else "Confirmar desactivación" if deactivate else "Guardar nombre", confirm, True))
        content.add_widget(button("Cancelar", popup.dismiss))
        popup.open()

    for row in app.store.list_categories(selected_kind, selected_scope, False):
        card = Card()
        card.add_widget(label(row["name"], 16, bold=True))
        card.add_widget(label(("Personalizada" if row["custom"] else "Predeterminada") + (" · Activa" if row["active"] else " · Inactiva"), 12, MUTED))
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        if row["custom"]:
            actions.add_widget(button("Editar nombre", lambda r=row: edit(r)))
        if row["active"]:
            actions.add_widget(button("Desactivar", lambda r=row: edit(r, True)))
        else:
            actions.add_widget(button("Activar", lambda r=row: edit(r, activate=True)))
        card.add_widget(actions)
        app.body.add_widget(card)
    app.body.add_widget(button("Volver a Hogar y ajustes", lambda: app.show("Hogar")))

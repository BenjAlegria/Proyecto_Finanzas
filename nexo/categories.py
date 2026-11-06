"""Reglas del catálogo y versión en memoria para la demo."""
import unicodedata


def category_name(name):
    name = unicodedata.normalize("NFC", " ".join(name.split()))
    if not name or len(name) > 60:
        raise ValueError("Escribe un nombre de categoría de 1 a 60 caracteres.")
    return name


def name_key(name):
    return category_name(name).casefold()


def validate_type_scope(kind, scope):
    if kind not in ("Ingreso", "Gasto") or scope not in ("Personal", "Familiar"):
        raise ValueError("Selecciona un tipo y ámbito válidos.")


class MemoryCategories:
    def __init__(self, defaults):
        self.rows = []
        for scope in ("Personal", "Familiar"):
            for kind, names in defaults.items():
                for name in names:
                    self.create(name, kind, scope, custom=False)

    def list(self, kind=None, scope=None, active_only=True):
        return [dict(row) for row in self.rows if (kind is None or row["kind"] == kind)
                and (scope is None or row["scope"] == scope) and (not active_only or row["active"])]

    def create(self, name, kind, scope, custom=True):
        validate_type_scope(kind, scope)
        name = category_name(name)
        if any(name_key(row["name"]) == name_key(name) and row["kind"] == kind and row["scope"] == scope for row in self.rows):
            raise ValueError("Ya existe una categoría con ese nombre, tipo y ámbito, incluso si está inactiva.")
        identity = len(self.rows) + 1
        self.rows.append(dict(id=identity, name=name, kind=kind, scope=scope, custom=custom, active=True))
        return identity

    def get(self, identity):
        for row in self.rows:
            if row["id"] == identity:
                return row
        raise ValueError("La categoría ya no existe.")

    def rename(self, identity, name):
        row = self.get(identity)
        if not row["custom"]:
            raise ValueError("Las categorías predeterminadas no se pueden renombrar.")
        name = category_name(name)
        if any(r["id"] != identity and r["kind"] == row["kind"] and r["scope"] == row["scope"]
               and name_key(r["name"]) == name_key(name) for r in self.rows):
            raise ValueError("Ya existe una categoría con ese nombre, tipo y ámbito.")
        row["name"] = name

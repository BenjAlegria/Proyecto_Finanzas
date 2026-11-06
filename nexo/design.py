"""Identidad visual y preferencias. No abre ni modifica SQLite."""
import json
import os
from pathlib import Path
from weakref import WeakKeyDictionary


def rgba(value):
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (1,)


PALETTES = {
    "Claro": dict(bg="F5F7FC", panel="FFFFFF", primary="4059C9", text="1D2941",
                  muted="6F7D94", on_primary="FFFFFF", income="157347", expense="B42336",
                  warning="805500", line="DCE2F0", soft="E8EDFF"),
    "Oscuro": dict(bg="141B2D", panel="232D42", primary="A6B6FF", text="F4F6FF",
                   muted="A9B6CF", on_primary="141B2D", income="73DCA5", expense="FF9CA7",
                   warning="FFD080", line="3B4964", soft="303E62"),
}


def system_theme():
    """Windows supported without extra dependencies; other platforms return None."""
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                return "Claro" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] else "Oscuro"
        except OSError:
            pass
    return None


class ThemeManager:
    def __init__(self):
        self.preference = "Claro"
        self.resolved = "Claro"
        self.path = None
        self.error = ""
        self._widgets = WeakKeyDictionary()

    @property
    def options(self):
        return ("Claro", "Oscuro", "Automático") if system_theme() else ("Claro", "Oscuro")

    def color(self, role):
        return rgba(PALETTES[self.resolved][role])

    def track(self, widget, **properties):
        self._widgets[widget] = properties
        self._apply(widget, properties)
        return widget

    def _apply(self, widget, properties):
        for name, role in properties.items():
            setattr(widget, name, self.color(role) if isinstance(role, str) else role)
        if hasattr(widget, "apply_theme"):
            widget.apply_theme()

    def load(self, path):
        self.path = Path(path)
        self.error = ""
        preference = "Claro"
        try:
            preference = json.loads(self.path.read_text(encoding="utf-8"))["theme"]
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError):
            self.error = "No se pudo leer la preferencia. Se usa el tema claro."
        if preference not in ("Claro", "Oscuro", "Automático"):
            preference = "Claro"
        self.set(preference, persist=False)

    def set(self, preference, persist=True):
        if preference not in ("Claro", "Oscuro", "Automático"):
            raise ValueError("Tema inválido")
        if persist and self.path:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.path.with_suffix(".tmp")
                temporary.write_text(json.dumps({"theme": preference}), encoding="utf-8")
                temporary.replace(self.path)
            except OSError as exc:
                raise OSError("No se pudo guardar la preferencia de tema.") from exc
        self.preference = preference
        self.refresh()

    def refresh(self, *_):
        self.resolved = (system_theme() or "Claro") if self.preference == "Automático" else self.preference
        for widget, properties in list(self._widgets.items()):
            self._apply(widget, properties)


theme = ThemeManager()

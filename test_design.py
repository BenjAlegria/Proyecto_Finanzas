from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from nexo.design import ThemeManager, PALETTES, rgba


class ThemeTests(unittest.TestCase):
    def test_preference_persists_without_database(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "appearance.json"
            manager = ThemeManager()
            manager.load(path)
            manager.set("Oscuro")
            restored = ThemeManager()
            restored.load(path)
            self.assertEqual(restored.resolved, "Oscuro")
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["appearance.json"])

    def test_live_colors(self):
        class Widget:
            pass
        widget = Widget()
        manager = ThemeManager()
        manager.track(widget, color="primary")
        self.assertEqual(widget.color, rgba("4059C9"))
        manager.set("Oscuro", persist=False)
        self.assertEqual(widget.color, rgba("A6B6FF"))
        self.assertEqual(manager.color("bg"), rgba("141B2D"))

    def test_automatic_and_fallback(self):
        manager = ThemeManager()
        with patch("nexo.design.system_theme", return_value="Oscuro"):
            manager.set("Automático", persist=False)
            self.assertEqual(manager.resolved, "Oscuro")
            self.assertIn("Automático", manager.options)
        with patch("nexo.design.system_theme", return_value="Claro"):
            manager.refresh()
            self.assertEqual(manager.resolved, "Claro")
        with patch("nexo.design.system_theme", return_value=None):
            manager.refresh()
            self.assertEqual(manager.resolved, "Claro")
            self.assertNotIn("Automático", manager.options)

    def test_bad_preference_and_write_error(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "appearance.json"
            path.write_text("not json", encoding="utf-8")
            manager = ThemeManager()
            manager.load(path)
            self.assertEqual(manager.resolved, "Claro")
            with patch.object(Path, "write_text", side_effect=OSError()):
                with self.assertRaises(OSError):
                    manager.set("Oscuro")
            self.assertEqual(manager.preference, "Claro")


if __name__ == "__main__":
    unittest.main()

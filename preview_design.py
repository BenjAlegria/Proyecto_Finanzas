"""Capturas de la primera etapa visual. Solo demo y preferencias temporales."""
import os
os.environ["KIVY_NO_FILELOG"] = "1"
from pathlib import Path
from tempfile import TemporaryDirectory
from kivy.clock import Clock
from kivy.core.window import Window
from nexo.app import NexoFinanzas
from nexo.design import theme


class PreviewApp(NexoFinanzas):
    failure = None

    def on_start(self):
        self.output = Path(__file__).parent / "docs" / "previews"
        self.output.mkdir(parents=True, exist_ok=True)
        self.cases = iter((mode, page, width, height)
                          for width, height, pages in ((430, 860, ("Inicio", "Personal", "Registrar", "Hogar", "Categorías")),
                                                       (360, 640, ("Registrar", "Hogar", "Categorías")))
                          for mode in ("Claro", "Oscuro") for page in pages)
        Clock.schedule_once(self.next_case, .5)

    def next_case(self, *_):
        case = next(self.cases, None)
        if case is None:
            self.stop()
            return
        mode, page, width, height = case
        try:
            Window.size = (width, height)
            theme.set(mode)
            self.show(page)
            if page == "Registrar":
                self.form_inputs["amount"].text = "25000"
                self.form_inputs["description"].text = "Compra de prueba"
                theme.set("Oscuro" if mode == "Claro" else "Claro", persist=False)
                theme.set(mode, persist=False)
                assert self.form_inputs["amount"].text == "25000"
                assert self.form_inputs["description"].text == "Compra de prueba"
                assert tuple(self.form_inputs["amount"].foreground_color) == theme.color("text")
            assert tuple(Window.clearcolor) == theme.color("bg")
            self.target = self.output / f"{page}-{mode}-{width}.png"
            Clock.schedule_once(self.capture, .25)
        except Exception as exc:
            self.failure = exc
            self.stop()

    def capture(self, *_):
        self.root.export_to_png(str(self.target))
        Clock.schedule_once(self.next_case, .1)


if __name__ == "__main__":
    with TemporaryDirectory() as folder:
        app = PreviewApp()
        app._user_data_dir = folder
        app.run()
        if app.failure:
            raise app.failure

"""Revisión de geometría y capturas reales de Hogar; solo demo temporal."""
import os
os.environ["KIVY_NO_FILELOG"] = "1"
from pathlib import Path
from tempfile import TemporaryDirectory
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from nexo.app import NexoFinanzas
from nexo.design import theme
from nexo.widgets import Card
from nexo.settings_widgets import OptionCard, RoundedField, RoundedButton


class SettingsReview(NexoFinanzas):
    failure = None

    def on_start(self):
        self.cases = iter((mode, width, height) for width, height in ((360, 640), (430, 860))
                          for mode in ("Claro", "Oscuro"))
        self.output = Path(__file__).parent / "docs" / "previews"
        self.output.mkdir(parents=True, exist_ok=True)
        Clock.schedule_once(self.next_case, .5)

    def next_case(self, *_):
        case = next(self.cases, None)
        if case is None:
            self.stop()
            return
        self.mode, self.width, self.height = case
        Window.size = (self.width, self.height)
        theme.set(self.mode, persist=False)
        self.show("Hogar")
        Clock.schedule_once(self.inspect, .3)

    def inspect(self, *_):
        try:
            shell = self.manager.current_screen.children[0]
            self.scroll = next(w for w in shell.children if isinstance(w, ScrollView))
            nav = shell.children[0]
            assert self.scroll.y >= nav.top
            cards = [w for w in reversed(self.body.children) if isinstance(w, Card)]
            assert len(cards) == 4
            assert cards[0].height <= dp(160), cards[0].height
            assert all(w.height <= dp(112) for w in cards[1:])
            assert not any(isinstance(w, RoundedButton) for w in cards[1].walk(restrict=True))
            assert isinstance(cards[1], OptionCard)
            entry = next(w for w in cards[0].walk(restrict=True) if isinstance(w, RoundedField))
            assert tuple(entry.foreground_color) == theme.color('text')
            # Exercise save and error feedback without touching a local database.
            entry.text = ''
            save = next(w for w in cards[0].walk(restrict=True) if isinstance(w, RoundedButton))
            save.dispatch('on_release')
            assert self.store.home == 'Hogar Rivera'
            entry.text = 'Hogar Rivera'
            save.dispatch('on_release')
            assert self.store.home == 'Hogar Rivera'
            self.show('Hogar')
            self.scroll = next(w for w in self.manager.current_screen.children[0].children if isinstance(w, ScrollView))
            Clock.schedule_once(self.capture_top, .2)
        except Exception as exc:
            self.failure = exc
            self.stop()

    def capture_top(self, *_):
        self.root.export_to_png(str(self.output / f'Hogar-{self.mode}-{self.width}.png'))
        self.scroll.scroll_y = 0
        Clock.schedule_once(self.capture_bottom, .2)

    def capture_bottom(self, *_):
        try:
            last = self.body.children[0]
            assert last.to_window(*last.pos)[1] >= self.scroll.y - dp(2)
            self.root.export_to_png(str(self.output / f'Hogar-{self.mode}-{self.width}-final.png'))
            Clock.schedule_once(self.next_case, .1)
        except Exception as exc:
            self.failure = exc
            self.stop()


if __name__ == '__main__':
    with TemporaryDirectory() as folder:
        app = SettingsReview()
        app._user_data_dir = folder
        app.run()
        if app.failure:
            raise app.failure
        print('OK: Hogar, alturas, guardado, navegación y desplazamiento en ambos temas.')


from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner

BG = (0.035, 0.06, 0.075, 1)
PANEL = (0.075, 0.115, 0.135, 1)
GREEN = (0.12, 0.77, 0.53, 1)
WHITE = (0.93, 0.96, 0.95, 1)
MUTED = (0.65, 0.73, 0.74, 1)


class Card(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(16), spacing=dp(10),
                         size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*PANEL)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self.rect.pos, self.rect.size = self.pos, self.size


def label(text, size=15, color=WHITE, bold=False):
    widget = Label(text=text, font_size=dp(size), color=color, bold=bold,
                   halign="left", valign="middle", size_hint_y=None)
    widget.bind(width=lambda obj, width: setattr(obj, "text_size", (width, None)))
    widget.bind(texture_size=lambda obj, value: setattr(obj, "height", max(dp(28), value[1] + dp(8))))
    return widget


def button(text, callback, primary=False):
    widget = Button(text=text, size_hint_y=None, height=dp(48), font_size=dp(14),
                    background_normal="", background_color=GREEN if primary else PANEL,
                    color=BG if primary else WHITE)
    widget.bind(on_release=lambda *_: callback())
    return widget


def field(hint, text=""):
    return TextInput(hint_text=hint, text=text, multiline=False, size_hint_y=None,
                     height=dp(48), padding=[dp(12), dp(12)], font_size=dp(16),
                     background_normal="", background_active="", background_color=PANEL,
                     foreground_color=WHITE, cursor_color=GREEN, hint_text_color=MUTED)


def select(values, text=None):
    return Spinner(text=text or values[0], values=values, size_hint_y=None,
                   height=dp(48), background_normal="", background_color=PANEL,
                   color=WHITE, font_size=dp(15))

from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup as KivyPopup
from kivy.uix.progressbar import ProgressBar as KivyProgressBar
from kivy.uix.screenmanager import Screen
from nexo.design import theme

# Semantic roles, resolved live by the centralized manager.
BG, PANEL, PRIMARY, WHITE, MUTED = 'bg', 'panel', 'primary', 'text', 'muted'


class ThemedScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self.fill = Color()
            self.surface = RoundedRectangle(pos=self.pos, size=self.size, radius=[0])
        self.bind(pos=self.sync, size=self.sync)
        theme.track(self)

    def sync(self, *_):
        self.surface.pos, self.surface.size = self.pos, self.size

    def apply_theme(self):
        self.fill.rgba = theme.color('bg')


class Card(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=dp(16), spacing=dp(6), size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter('height'))
        with self.canvas.before:
            self.fill = Color()
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        self.bind(pos=self._sync, size=self._sync)
        theme.track(self)

    def apply_theme(self):
        self.fill.rgba = theme.color('panel')

    def _sync(self, *_):
        self.rect.pos, self.rect.size = self.pos, self.size


def label(text, size=15, color=WHITE, bold=False):
    widget = Label(text=text, font_size=dp(size), bold=bold, halign='left', valign='middle', size_hint_y=None, height=dp(22))
    widget.bind(width=lambda obj, width: setattr(obj, 'text_size', (width, None)))
    widget.bind(texture_size=lambda obj, value: setattr(obj, 'height', max(dp(22), value[1] + dp(4))))
    return theme.track(widget, color=color)


def button(text, callback, primary=False):
    widget = Button(text=text, size_hint_y=None, height=dp(44), font_size=dp(14), background_normal='', background_down='')
    theme.track(widget, background_color='primary' if primary else 'soft', color='on_primary' if primary else 'primary')
    widget.bind(on_release=lambda *_: callback())
    return widget


def field(hint, text=''):
    widget = TextInput(hint_text=hint, text=text, multiline=False, size_hint_y=None, height=dp(44),
                      padding=[dp(12), dp(10)], font_size=dp(16), background_normal='', background_active='')
    return theme.track(widget, background_color='panel', foreground_color='text', cursor_color='primary',
                       hint_text_color='muted', selection_color='soft')


class MenuOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = self.background_down = ''
        self.height = dp(44)
        theme.track(self, background_color='panel', color='text')


def select(values, text=None):
    widget = Spinner(text=text or values[0], values=values, option_cls=MenuOption, size_hint_y=None,
                     height=dp(44), background_normal='', background_down='', font_size=dp(15))
    return theme.track(widget, background_color='panel', color='text')


class Popup(KivyPopup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background = ''
        theme.track(self, background_color='panel', title_color='text', separator_color='primary')


class ProgressBar(KivyProgressBar):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.canvas.clear()
        with self.canvas:
            self.track_color = Color()
            self.track_rect = RoundedRectangle(radius=[dp(5)])
            self.bar_color = Color()
            self.bar_rect = RoundedRectangle(radius=[dp(5)])
        self.bind(pos=self._sync, size=self._sync, value=self._sync, max=self._sync)
        theme.track(self)

    def apply_theme(self):
        self.track_color.rgba = theme.color('soft')
        self.bar_color.rgba = theme.color('primary')

    def _sync(self, *_):
        self.track_rect.pos, self.track_rect.size = self.pos, self.size
        self.bar_rect.pos = self.pos
        self.bar_rect.size = (self.width * min(1, self.value / self.max) if self.max else 0, self.height)


def heading(title, subtitle):
    box = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_y=None)
    box.bind(minimum_height=box.setter('height'))
    box.add_widget(label(title, 25, bold=True))
    box.add_widget(label(subtitle, 13, MUTED))
    return box


def indicator(title, amount, role):
    box = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_y=None)
    box.bind(minimum_height=box.setter('height'))
    box.add_widget(label(title, 12, MUTED))
    box.add_widget(label(amount, 19, role, True))
    return box


class NavButton(Button):
    """Vector icons avoid missing-glyph fonts or additional assets."""
    def __init__(self, target, text, callback, active=False):
        super().__init__(text=text, font_size=dp(11), halign='center', valign='bottom',
                         padding=[0, dp(5)], background_normal='', background_down='')
        self.target = target
        with self.canvas.after:
            self.ink = Color()
            self.icon = Line(width=dp(1.25))
        self.active = active
        self.bind(pos=self.draw_icon, size=self.draw_icon)
        self.bind(on_release=lambda *_: callback())
        theme.track(self, background_color='soft' if active else 'panel', color='primary' if active else 'muted')

    def apply_theme(self):
        self.ink.rgba = theme.color('primary' if self.active else 'muted')

    def draw_icon(self, *_):
        self.text_size = self.size
        x, y, u = self.center_x, self.top - dp(19), dp(8)
        points = {
            'Inicio': [x-u,y, x,y+u, x+u,y, x+u,y-u, x-u,y-u, x-u,y],
            'Personal': [x-u,y-u, x-u,y, x+u,y, x+u,y-u, x-u,y-u, x,y+u, x-u/2,y+u/2, x,y, x+u/2,y+u/2, x,y+u],
            'Registrar': [x-u,y, x+u,y, x,y, x,y+u, x,y-u],
            'Historial': [x-u,y+u, x+u,y+u, x+u,y-u, x-u,y-u, x-u,y+u, x-u/2,y+u/3, x+u/2,y+u/3, x-u/2,y-u/3, x+u/2,y-u/3],
            'Hogar': [x-u,y-u, x+u,y+u, x,y+u, x+u,y, x+u,y+u],
        }
        self.icon.points = points[self.target]


def navigation(current, callback):
    box = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(4))
    for target in ('Inicio', 'Personal', 'Registrar', 'Historial', 'Hogar'):
        box.add_widget(NavButton(target, 'Nuevo' if target == 'Registrar' else target,
                                lambda name=target: callback(name), current == target))
    return box


def segmented(options, selected, callback):
    """Two compact, equally sized touch targets with a visible selected state."""
    row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
    for value in options:
        row.add_widget(button(value, lambda option=value: callback(option), value == selected))
    return row


def settings_card(title, description, icon, callback=None):
    card = Card()
    row = BoxLayout(spacing=dp(10), size_hint_y=None)
    row.bind(minimum_height=row.setter('height'))
    symbol = NavButton(icon, '', lambda: None)
    symbol.size_hint = (None, None)
    symbol.width, symbol.height = dp(32), dp(44)
    symbol.disabled = True
    symbol.background_disabled_normal = ''
    row.add_widget(symbol)
    text = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1))
    text.bind(minimum_height=text.setter('height'))
    if callback:
        title_button = button(title, callback)
        title_button.halign = 'left'
        title_button.bind(size=lambda obj, size: setattr(obj, 'text_size', size))
        text.add_widget(title_button)
    else:
        text.add_widget(label(title, 17, bold=True))
    text.add_widget(label(description, 12, MUTED))
    row.add_widget(text)
    card.add_widget(row)
    return card

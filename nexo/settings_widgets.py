"""Componentes de ajustes. Opt-in: no cambia los controles de otras pantallas."""
from kivy.graphics import Canvas, Color, RoundedRectangle, Line
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from nexo.design import theme
from nexo.widgets import Card, label, MenuOption


class RoundedSurface:
    def setup_surface(self, role, border=False):
        self.surface_role = role
        self.has_border = border
        self.background_normal = self.background_down = ''
        if isinstance(self, TextInput):
            self.background_active = ''
        self.background_color = (0, 0, 0, 0)
        # Draw behind Kivy's native cursor/text instructions, preserving their colors.
        self.surface_canvas = Canvas()
        self.canvas.before.insert(0, self.surface_canvas)
        with self.surface_canvas:
            self.surface_color = Color()
            self.surface = RoundedRectangle(radius=[dp(12)])
            self.border_color = Color()
            self.border_line = Line(width=dp(1))
            Color(1, 1, 1, 1)
        self.bind(pos=self.sync_surface, size=self.sync_surface)
        if isinstance(self, TextInput):
            self.bind(focus=lambda *_: self.apply_theme())
        self.sync_surface()

    def sync_surface(self, *_):
        self.surface.pos, self.surface.size = self.pos, self.size
        self.border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(12))

    def apply_theme(self):
        self.surface_color.rgba = theme.color(self.surface_role)
        role = 'primary' if getattr(self, 'focus', False) else 'line'
        self.border_color.rgba = theme.color(role) if self.has_border else (0, 0, 0, 0)


class RoundedButton(RoundedSurface, Button):
    def __init__(self, text, callback, primary=False, **kwargs):
        super().__init__(text=text, size_hint_y=None, height=dp(44), font_size=dp(14), **kwargs)
        self.setup_surface('primary' if primary else 'soft')
        theme.track(self, color='on_primary' if primary else 'primary')
        self.bind(on_release=lambda *_: callback())


class RoundedField(RoundedSurface, TextInput):
    def __init__(self, hint, text='', **kwargs):
        super().__init__(text=text, hint_text=hint, multiline=False, size_hint_y=None,
                         height=dp(44), font_size=dp(15), padding=[dp(12), dp(11)], **kwargs)
        self.setup_surface('bg', border=True)
        theme.track(self, foreground_color='text', hint_text_color='muted', cursor_color='primary', selection_color='soft')


class RoundedSelect(RoundedSurface, Spinner):
    def __init__(self, values, text, **kwargs):
        super().__init__(values=values, text=text, option_cls=MenuOption, size_hint_y=None,
                         height=dp(44), font_size=dp(14), **kwargs)
        self.setup_surface('soft')
        theme.track(self, color='primary')


class SettingIcon(Widget):
    def __init__(self, kind, **kwargs):
        super().__init__(size_hint=(None, None), size=(dp(36), dp(36)), **kwargs)
        self.kind = kind
        with self.canvas:
            self.fill = Color()
            self.tile = RoundedRectangle(radius=[dp(11)])
            self.ink = Color()
            self.lines = [Line(width=dp(1.2)) for _ in range(4)]
        self.bind(pos=self.draw, size=self.draw)
        theme.track(self)

    def apply_theme(self):
        self.fill.rgba, self.ink.rgba = theme.color('soft'), theme.color('primary')

    def draw(self, *_):
        self.tile.pos, self.tile.size = self.pos, self.size
        x, y, u = self.center_x, self.center_y, dp(8)
        paths = {
            'home': [[x-u,y, x,y+u, x+u,y], [x-u+2,y-1, x-u+2,y-u, x+u-2,y-u, x+u-2,y-1]],
            'categories': [[x-u,y+u, x-u/4,y+u, x-u/4,y+u/4, x-u,y+u/4, x-u,y+u],
                           [x+u/4,y+u, x+u,y+u, x+u,y+u/4, x+u/4,y+u/4, x+u/4,y+u],
                           [x-u,y-u/4, x-u/4,y-u/4, x-u/4,y-u, x-u,y-u, x-u,y-u/4],
                           [x+u/4,y-u/4, x+u,y-u/4, x+u,y-u, x+u/4,y-u, x+u/4,y-u/4]],
            'appearance': [[x,y+u, x+u,y, x,y-u, x-u,y, x,y+u], [x,y+u, x,y-u]],
            'privacy': [[x-u,y+u, x+u,y+u, x+u,y, x,y-u, x-u,y, x-u,y+u],
                        [x-u/2,y, x-u/6,y-u/3, x+u/2,y+u/3]],
        }
        for line, points in zip(self.lines, paths[self.kind] + [[]] * 4):
            line.points = points


class SettingsHeader(BoxLayout):
    def __init__(self, title, description, icon, trailing=None, **kwargs):
        super().__init__(size_hint_y=None, spacing=dp(12), **kwargs)
        self.add_widget(SettingIcon(icon))
        self.copy = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        self.copy.bind(minimum_height=self.copy.setter('height'))
        self.copy.add_widget(label(title, 16, bold=True))
        self.description = label(description, 12, 'muted')
        self.copy.add_widget(self.description)
        self.add_widget(self.copy)
        self.copy.bind(height=self.fit)
        if trailing:
            self.add_widget(trailing)
        self.fit()

    def fit(self, *_):
        self.height = max(dp(44), self.copy.height)


class OptionCard(ButtonBehavior, Card):
    def __init__(self, title, description, icon, callback, **kwargs):
        super().__init__(**kwargs)
        self.text = title
        arrow = label('›', 24, 'muted')
        arrow.size_hint_x, arrow.width = None, dp(18)
        self.add_widget(SettingsHeader(title, description, icon, arrow))
        self.bind(on_release=lambda *_: callback())


def settings_panel(title, description, icon):
    card = Card()
    card.spacing = dp(12)
    card.add_widget(SettingsHeader(title, description, icon))
    return card


def feedback():
    widget = label('', 12, 'primary')
    def fit(*_):
        widget.height = widget.texture_size[1] + dp(4) if widget.text else 0
    widget.bind(text=fit, texture_size=fit)
    fit()
    return widget

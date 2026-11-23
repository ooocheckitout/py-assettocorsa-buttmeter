import ac, acsys

from render import Color, Position, Size
from settings import Settings, Threshold, save_settings
from telemetry import read_snapshot
from apps.widget import level


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def guidance_bar(position: Position, left_color: Color, right_color: Color) -> None:
    size = Size(320, 20)
    base_color = Color.grey

    # purple gradient bar
    ac.glColor4f(left_color.red, left_color.green, left_color.blue, left_color.alpha)
    ac.glQuad(position.x, position.y, size.width * 0.1, size.height)
    ac.glBegin(acsys.GL.Quads)
    ac.glVertex2f(position.x + size.width * 0.1, position.y)
    ac.glVertex2f(position.x + size.width * 0.1, position.y + size.height)
    ac.glColor4f(base_color.red, base_color.green, base_color.blue, base_color.alpha)
    ac.glVertex2f(position.x + size.width * 0.3, position.y + size.height)
    ac.glVertex2f(position.x + size.width * 0.3, position.y)
    ac.glEnd()

    # grey bar
    ac.glQuad(position.x + size.width * 0.3, position.y, size.width * 0.4, size.height)

    # amber gradient bar
    ac.glBegin(acsys.GL.Quads)
    ac.glVertex2f(position.x + size.width * 0.7, position.y)
    ac.glVertex2f(position.x + size.width * 0.7, position.y + size.height)
    ac.glColor4f(right_color.red, right_color.green, right_color.blue, right_color.alpha)
    ac.glVertex2f(position.x + size.width * 0.9, position.y + size.height)
    ac.glVertex2f(position.x + size.width * 0.9, position.y)
    ac.glEnd()
    ac.glQuad(position.x + size.width * 0.9, position.y, size.width * 0.1, size.height)

    # ticks
    tick_color = Color.white
    tick_size = Size(1, size.height + 8)
    tick_position = Position(position.x - tick_size.width / 2, position.y - 4)

    ac.glColor4f(tick_color.red, tick_color.green, tick_color.blue, tick_color.alpha)

    ac.glQuad(tick_position.x + size.width * 0.5, tick_position.y, tick_size.width, tick_size.height)

    ac.glQuad(tick_position.x + size.width * 0.1, tick_position.y, tick_size.width, tick_size.height)
    ac.glQuad(tick_position.x + size.width * 0.3, tick_position.y, tick_size.width, tick_size.height)
    ac.glQuad(tick_position.x + size.width * 0.7, tick_position.y, tick_size.width, tick_size.height)
    ac.glQuad(tick_position.x + size.width * 0.9, tick_position.y, tick_size.width, tick_size.height)


def marker(position: Position, value: float, limit: float, threshold: Threshold, color: Color) -> None:
    size = Size(284, 2)

    # line
    ac.glColor4f(1.0, 1.0, 1.0, 0.15)
    ac.glQuad(position.x, position.y, size.width, size.height)

    # marker
    ac.glColor4f(0.9, 0.9, 0.9, 0.85)
    ac.glQuad(position.x + size.width * (0.5 + clamp(value, -limit, limit) / limit / 2) - 2, position.y + size.height / 2 - 6, 4, 12)  # fmt: skip

    # indicator
    fill = Color.grey.mix(color, level(threshold, value))
    ac.glColor4f(fill.red, fill.green, fill.blue, fill.alpha)
    ac.glQuad(position.x + 296, position.y - 6, 24, 14)


def ratio_marker(position: Position, ratio: float, limit: float, settings: Settings) -> None:
    if ratio < 0:
        marker(position, ratio, limit, settings.lock, Color.purple)
    else:
        marker(position, ratio, limit, settings.spin, Color.amber)


def bar_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y + 1)
    ac.setSize(label, 96, 20)
    ac.setFontSize(label, 16)
    ac.setFontAlignment(label, "left")


def tick_label_left(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y - 24)
    ac.setSize(label, 100, 16)
    ac.setFontSize(label, 12)
    ac.setFontAlignment(label, "left")


def tick_label_center(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x - 50, position.y - 24)
    ac.setSize(label, 100, 16)
    ac.setFontSize(label, 12)
    ac.setFontAlignment(label, "center")


def tick_label_right(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x - 100, position.y - 24)
    ac.setSize(label, 100, 16)
    ac.setFontSize(label, 12)
    ac.setFontAlignment(label, "right")


def marker_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y - 7)
    ac.setSize(label, 88, 16)
    ac.setFontSize(label, 12)
    ac.setFontAlignment(label, "left")


def threshold_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y + 2)
    ac.setSize(label, 88, 16)
    ac.setFontSize(label, 14)
    ac.setFontAlignment(label, "left")


class SettingsApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        self.id = ac.newApp("Butt Meter Settings")

        ac.setSize(self.id, 456, 832)

        self.listeners = []

        self.threshold_steppers(Position(24, 200), "Lock", self.settings.lock, 0.01, self.on_lock_change)
        self.threshold_steppers(Position(24, 248), "Spin", self.settings.spin, 0.01, self.on_spin_change)
        self.threshold_steppers(Position(24, 436), "Understeer", self.settings.understeer, 1.0, self.on_understeer_change)  # fmt: skip
        self.threshold_steppers(Position(24, 624), "Oversteer", self.settings.oversteer, 1.0, self.on_oversteer_change)
        self.threshold_steppers(Position(24, 796), "Rotation", self.settings.body_slip, 1.0, self.on_body_slip_change)

        bar_label(self.id, Position(16, 64), "Slip ratio")
        bar_label(self.id, Position(16, 332), "Slip angle")
        bar_label(self.id, Position(16, 520), "Slip angle")
        bar_label(self.id, Position(16, 708), "Body slip")

        tick_label_center(self.id, Position(280, 64), "Grip")
        tick_label_center(self.id, Position(280, 332), "Grip")
        tick_label_center(self.id, Position(280, 520), "Grip")
        tick_label_center(self.id, Position(280, 708), "Straight")

        tick_label_left(self.id, Position(120, 64), "Lock")
        tick_label_right(self.id, Position(440, 64), "Spin")
        tick_label_left(self.id, Position(120, 332), "Understeer")
        tick_label_right(self.id, Position(440, 332), "Understeer")
        tick_label_left(self.id, Position(120, 520), "Oversteer")
        tick_label_right(self.id, Position(440, 520), "Oversteer")
        tick_label_left(self.id, Position(120, 708), "Rotation")
        tick_label_right(self.id, Position(440, 708), "Rotation")

        marker_label(self.id, Position(24, 104), "FL")
        marker_label(self.id, Position(24, 120), "FR")
        marker_label(self.id, Position(24, 136), "RL")
        marker_label(self.id, Position(24, 152), "RR")

        marker_label(self.id, Position(24, 372), "FL")
        marker_label(self.id, Position(24, 388), "FR")

        marker_label(self.id, Position(24, 560), "RL")
        marker_label(self.id, Position(24, 576), "RR")

        marker_label(self.id, Position(24, 748), "Slip")

        # AC does not hold a reference to callbacks, so keep the bound method alive
        self.callback = self.render
        ac.addRenderCallback(self.id, self.callback)

    def threshold_steppers(self, position: Position, title: str, threshold: Threshold, step: float, on_change: object) -> None:  # fmt: skip
        threshold_label(self.id, position, title)

        def on_start_change(value: float) -> None:
            threshold.start = value
            on_change(threshold)

        def on_end_change(value: float) -> None:
            threshold.end = value
            on_change(threshold)

        self.stepper(Position(position.x + 96, position.y), "start", threshold.start, step, on_start_change)
        self.stepper(Position(position.x + 316, position.y), "end", threshold.end, step, on_end_change)

    def stepper(self, position: Position, title: str, value: float, step: float, on_change: object) -> None:
        title_label = ac.addLabel(self.id, title)
        ac.setPosition(title_label, position.x, position.y - 20)
        ac.setSize(title_label, 100, 16)
        ac.setFontSize(title_label, 12)
        ac.setFontAlignment(title_label, "center")

        value_label = ac.addLabel(self.id, "{:.2f}".format(value))
        ac.setPosition(value_label, position.x + 20, position.y + 2)
        ac.setSize(value_label, 60, 16)
        ac.setFontSize(value_label, 14)
        ac.setFontAlignment(value_label, "center")

        def change(delta: float) -> None:
            nonlocal value
            value = round(value + delta, 2)
            on_change(value)
            ac.setText(value_label, "{:.2f}".format(value))

        on_minus = lambda x, y: change(-step)
        on_plus = lambda x, y: change(step)

        button_size = Size(20, 20)

        minus_button = ac.addButton(self.id, "-")
        ac.setPosition(minus_button, position.x, position.y)
        ac.setSize(minus_button, button_size.width, button_size.height)
        ac.addOnClickedListener(minus_button, on_minus)

        plus_button = ac.addButton(self.id, "+")
        ac.setPosition(plus_button, position.x + 80, position.y)
        ac.setSize(plus_button, button_size.width, button_size.height)
        ac.addOnClickedListener(plus_button, on_plus)

        self.listeners.extend((on_minus, on_plus))

    def on_lock_change(self, threshold: Threshold) -> None:
        self.settings.lock = threshold
        save_settings(self.settings)

    def on_spin_change(self, threshold: Threshold) -> None:
        self.settings.spin = threshold
        save_settings(self.settings)

    def on_understeer_change(self, threshold: Threshold) -> None:
        self.settings.understeer = threshold
        save_settings(self.settings)

    def on_oversteer_change(self, threshold: Threshold) -> None:
        self.settings.oversteer = threshold
        save_settings(self.settings)

    def on_body_slip_change(self, threshold: Threshold) -> None:
        self.settings.body_slip = threshold
        save_settings(self.settings)

    def render(self, _: float) -> None:
        snapshot = read_snapshot()

        guidance_bar(Position(120, 64), Color.purple, Color.amber)
        guidance_bar(Position(120, 332), Color.teal, Color.teal)
        guidance_bar(Position(120, 520), Color.red, Color.red)
        guidance_bar(Position(120, 708), Color.red, Color.red)

        fl, fr, rl, rr = snapshot.wheels
        settings = self.settings

        ratio_marker(Position(120, 104), fl.slip_ratio, 0.125, settings)
        ratio_marker(Position(120, 120), fr.slip_ratio, 0.125, settings)
        ratio_marker(Position(120, 136), rl.slip_ratio, 0.125, settings)
        ratio_marker(Position(120, 152), rr.slip_ratio, 0.125, settings)

        marker(Position(120, 372), fl.slip_angle, 12.5, settings.understeer, Color.teal)
        marker(Position(120, 388), fr.slip_angle, 12.5, settings.understeer, Color.teal)

        marker(Position(120, 560), rl.slip_angle, 12.5, settings.oversteer, Color.red)
        marker(Position(120, 576), rr.slip_angle, 12.5, settings.oversteer, Color.red)

        marker(Position(120, 748), snapshot.body_slip, 12.5, settings.body_slip, Color.red)

import ac, acsys

from render import Color, Position, Size
from settings import Settings, Threshold, save_settings, slip_ratio_fill, threshold_fill
from telemetry import read_snapshot


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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


def bar_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y + 1)
    ac.setSize(label, 96, 20)
    ac.setFontSize(label, 16)
    ac.setFontAlignment(label, "left")


def draw_guidance_block(position: Position, size: Size, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x, position.y, size.width, size.height)


def draw_guidance_gradient(position: Position, size: Size, start_color: Color, end_color: Color) -> None:
    ac.glBegin(acsys.GL.Quads)
    ac.glColor4f(start_color.red, start_color.green, start_color.blue, start_color.alpha)
    ac.glVertex2f(position.x, position.y)
    ac.glVertex2f(position.x, position.y + size.height)
    ac.glColor4f(end_color.red, end_color.green, end_color.blue, end_color.alpha)
    ac.glVertex2f(position.x + size.width, position.y + size.height)
    ac.glVertex2f(position.x + size.width, position.y)
    ac.glEnd()


def draw_guidance_tick(position: Position, size: Size, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x - size.width / 2, position.y, size.width, size.height)


def draw_guidance_bar(position: Position, left_color: Color, right_color: Color) -> None:
    size = Size(320, 20)
    tick = Size(1, size.height + 8)

    end = Size(size.width * 0.1, size.height)
    fade = Size(size.width * 0.2, size.height)
    middle = Size(size.width * 0.4, size.height)

    draw_guidance_block(position, end, left_color)
    draw_guidance_gradient(Position(position.x + end.width, position.y), fade, left_color, Color.grey)
    draw_guidance_block(Position(position.x + end.width + fade.width, position.y), middle, Color.grey)
    draw_guidance_gradient(Position(position.x + end.width + fade.width + middle.width, position.y), fade, Color.grey, right_color)  # fmt: skip
    draw_guidance_block(Position(position.x + size.width - end.width, position.y), end, right_color)

    for fraction in (0.1, 0.3, 0.5, 0.7, 0.9):
        draw_guidance_tick(Position(position.x + size.width * fraction, position.y - 4), tick, Color.white)


def marker_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y - 7)
    ac.setSize(label, 88, 16)
    ac.setFontSize(label, 12)
    ac.setFontAlignment(label, "left")


def draw_marker_line(position: Position, size: Size, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x, position.y, size.width, size.height)


def draw_marker_knob(center: Position, size: Size, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(center.x - size.width / 2, center.y - size.height / 2, size.width, size.height)


def draw_marker_indicator(position: Position, size: Size, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x, position.y - size.height / 2, size.width, size.height)


def draw_marker(position: Position, progress: float, fill: Color) -> None:
    line = Size(284, 2)
    middle = position.y + line.height / 2

    draw_marker_line(position, line, Color.white.brightness(0.15))
    draw_marker_knob(Position(position.x + line.width * progress, middle), Size(4, 12), Color.white)
    draw_marker_indicator(Position(position.x + line.width + 12, middle), Size(24, 14), fill)


def marker_progress(value: float, limit: float) -> float:
    return 0.5 + clamp(value, -limit, limit) / limit / 2


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

        tick_label_left(self.id, Position(120, 64), "Lock")
        tick_label_center(self.id, Position(280, 64), "Grip")
        tick_label_right(self.id, Position(440, 64), "Spin")
        bar_label(self.id, Position(16, 64), "Slip ratio")
        marker_label(self.id, Position(24, 104), "FL")
        marker_label(self.id, Position(24, 120), "FR")
        marker_label(self.id, Position(24, 136), "RL")
        marker_label(self.id, Position(24, 152), "RR")
        self.threshold_steppers(Position(24, 200), "Lock", self.settings.lock, 0.01, self.on_lock_change)
        self.threshold_steppers(Position(24, 248), "Spin", self.settings.spin, 0.01, self.on_spin_change)

        tick_label_left(self.id, Position(120, 332), "Understeer")
        tick_label_center(self.id, Position(280, 332), "Grip")
        tick_label_right(self.id, Position(440, 332), "Understeer")
        bar_label(self.id, Position(16, 332), "Slip angle")
        marker_label(self.id, Position(24, 372), "FL")
        marker_label(self.id, Position(24, 388), "FR")
        self.threshold_steppers(Position(24, 436), "Understeer", self.settings.understeer, 1.0, self.on_understeer_change)  # fmt: skip

        tick_label_left(self.id, Position(120, 520), "Oversteer")
        tick_label_center(self.id, Position(280, 520), "Grip")
        tick_label_right(self.id, Position(440, 520), "Oversteer")
        bar_label(self.id, Position(16, 520), "Slip angle")
        marker_label(self.id, Position(24, 560), "RL")
        marker_label(self.id, Position(24, 576), "RR")
        self.threshold_steppers(Position(24, 624), "Oversteer", self.settings.oversteer, 1.0, self.on_oversteer_change)

        tick_label_left(self.id, Position(120, 708), "Rotation")
        tick_label_center(self.id, Position(280, 708), "Straight")
        tick_label_right(self.id, Position(440, 708), "Rotation")
        bar_label(self.id, Position(16, 708), "Body slip")
        marker_label(self.id, Position(24, 748), "Slip")
        self.threshold_steppers(Position(24, 796), "Rotation", self.settings.body_slip, 1.0, self.on_body_slip_change)

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

        fl, fr, rl, rr = snapshot.wheels
        settings = self.settings

        draw_guidance_bar(Position(120, 64), Color.purple, Color.amber)
        draw_marker(Position(120, 104), marker_progress(fl.slip_ratio, 0.125), slip_ratio_fill(fl.slip_ratio, settings.lock, settings.spin))  # fmt: skip
        draw_marker(Position(120, 120), marker_progress(fr.slip_ratio, 0.125), slip_ratio_fill(fr.slip_ratio, settings.lock, settings.spin))  # fmt: skip
        draw_marker(Position(120, 136), marker_progress(rl.slip_ratio, 0.125), slip_ratio_fill(rl.slip_ratio, settings.lock, settings.spin))  # fmt: skip
        draw_marker(Position(120, 152), marker_progress(rr.slip_ratio, 0.125), slip_ratio_fill(rr.slip_ratio, settings.lock, settings.spin))  # fmt: skip

        draw_guidance_bar(Position(120, 332), Color.teal, Color.teal)
        draw_marker(Position(120, 372), marker_progress(fl.slip_angle, 12.5), threshold_fill(fl.slip_angle, settings.understeer, Color.teal))  # fmt: skip
        draw_marker(Position(120, 388), marker_progress(fr.slip_angle, 12.5), threshold_fill(fr.slip_angle, settings.understeer, Color.teal))  # fmt: skip

        draw_guidance_bar(Position(120, 520), Color.red, Color.red)
        draw_marker(Position(120, 560), marker_progress(rl.slip_angle, 12.5), threshold_fill(rl.slip_angle, settings.oversteer, Color.red))  # fmt: skip
        draw_marker(Position(120, 576), marker_progress(rr.slip_angle, 12.5), threshold_fill(rr.slip_angle, settings.oversteer, Color.red))  # fmt: skip

        draw_guidance_bar(Position(120, 708), Color.red, Color.red)
        draw_marker(Position(120, 748), marker_progress(snapshot.body_slip, 12.5), threshold_fill(snapshot.body_slip, settings.body_slip, Color.red))  # fmt: skip

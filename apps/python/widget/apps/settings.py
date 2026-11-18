import ac, acsys

from render import Color, Position, Size
from settings import Settings, Threshold, save_settings
from telemetry import Snapshot, read_snapshot


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def guidance_bar(position: Position, size: Size, left_color: Color, right_color: Color) -> None:
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


def marker(position: Position, size: Size, ratio: float, limit: float) -> None:
    # line
    ac.glColor4f(1.0, 1.0, 1.0, 0.15)
    ac.glQuad(position.x, position.y, size.width, size.height)

    # marker
    ac.glColor4f(0.9, 0.9, 0.9, 0.85)
    ac.glQuad(position.x + size.width * (0.5 + clamp(ratio, -limit, limit) / limit / 2) - 2, position.y + size.height / 2 - 6, 4, 12)  # fmt: skip


def bar_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y + 2)
    ac.setSize(label, 75, 16)
    ac.setFontSize(label, 14)
    ac.setFontAlignment(label, "left")


def tick_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x - 20, position.y - 20)
    ac.setSize(label, 40, 16)
    ac.setFontSize(label, 12)
    ac.setFontAlignment(label, "center")


def marker_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y - 7)
    ac.setSize(label, 60, 16)
    ac.setFontSize(label, 12)
    ac.setFontAlignment(label, "left")


def threshold_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y + 1)
    ac.setSize(label, 75, 16)
    ac.setFontSize(label, 14)
    ac.setFontAlignment(label, "left")


def stepper_title_label(app_id: int, position: Position, text: str) -> None:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x, position.y - 18)
    ac.setSize(label, 100, 20)
    ac.setFontSize(label, 12)
    ac.setFontAlignment(label, "center")


def stepper_value_label(app_id: int, position: Position, text: str) -> int:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, position.x + 20, position.y)
    ac.setSize(label, 60, 20)
    ac.setFontSize(label, 14)
    ac.setFontAlignment(label, "center")
    return label


def stepper_minus_button(app_id: int, position: Position, on_click: object) -> None:
    button = ac.addButton(app_id, "-")
    ac.setPosition(button, position.x, position.y)
    ac.setSize(button, 20, 20)
    ac.addOnClickedListener(button, on_click)


def stepper_plus_button(app_id: int, position: Position, on_click: object) -> None:
    button = ac.addButton(app_id, "+")
    ac.setPosition(button, position.x + 80, position.y)
    ac.setSize(button, 20, 20)
    ac.addOnClickedListener(button, on_click)


class SettingsApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        self.id = ac.newApp("AlligatorRacing_Settings")

        ac.setSize(self.id, 365, 597)

        self.listeners = []

        self.threshold_steppers(Position(10, 180), "Lock", self.settings.lock, self.on_lock_change)
        self.threshold_steppers(Position(10, 230), "Spin", self.settings.spin, self.on_spin_change)
        self.threshold_steppers(Position(10, 420), "Angle", self.settings.slip_angle, self.on_slip_angle_change)
        self.threshold_steppers(Position(10, 562), "Yaw", self.settings.yaw_rate, self.on_yaw_rate_change)

        bar_label(self.id, Position(10, 55), "Slip ratio")
        bar_label(self.id, Position(10, 295), "Slip angle")
        bar_label(self.id, Position(10, 485), "Yaw rate")

        tick_label(self.id, Position(220, 55), "Grip")
        tick_label(self.id, Position(220, 295), "Grip")
        tick_label(self.id, Position(220, 485), "Straight")

        tick_label(self.id, Position(98, 55), "Lock")
        tick_label(self.id, Position(342, 55), "Spin")
        tick_label(self.id, Position(98, 295), "Slide")
        tick_label(self.id, Position(342, 295), "Slide")
        tick_label(self.id, Position(98, 485), "Rotation")
        tick_label(self.id, Position(342, 485), "Rotation")

        marker_label(self.id, Position(10, 92), "FL")
        marker_label(self.id, Position(10, 108), "FR")
        marker_label(self.id, Position(10, 124), "RL")
        marker_label(self.id, Position(10, 140), "RR")

        marker_label(self.id, Position(10, 332), "FL")
        marker_label(self.id, Position(10, 348), "FR")
        marker_label(self.id, Position(10, 364), "RL")
        marker_label(self.id, Position(10, 380), "RR")

        marker_label(self.id, Position(10, 522), "Yaw")

        # AC does not hold a reference to callbacks, so keep the bound method alive
        self.callback = self.render
        ac.addRenderCallback(self.id, self.callback)

    def threshold_steppers(self, position: Position, title: str, threshold: Threshold, on_change: object) -> None:
        threshold_label(self.id, position, title)

        def on_start_change(value: float) -> None:
            threshold.start = value
            on_change(threshold)

        def on_end_change(value: float) -> None:
            threshold.end = value
            on_change(threshold)

        self.stepper(Position(position.x + 75, position.y), "start", threshold.start, on_start_change)
        self.stepper(Position(position.x + 245, position.y), "end", threshold.end, on_end_change)

    def stepper(self, position: Position, title: str, value: float, on_change: object) -> None:
        stepper_title_label(self.id, position, title)
        value_label = stepper_value_label(self.id, position, "{:.2f}".format(value))

        def change(delta: float) -> None:
            nonlocal value
            value = round(value + delta, 2)
            on_change(value)
            ac.setText(value_label, "{:.2f}".format(value))

        step = 0.01
        on_minus = lambda x, y: change(-step)
        on_plus = lambda x, y: change(step)

        stepper_minus_button(self.id, position, on_minus)
        stepper_plus_button(self.id, position, on_plus)

        self.listeners.extend((on_minus, on_plus))

    def on_lock_change(self, threshold: Threshold) -> None:
        self.settings.lock = threshold
        save_settings(self.settings)

    def on_spin_change(self, threshold: Threshold) -> None:
        self.settings.spin = threshold
        save_settings(self.settings)

    def on_slip_angle_change(self, threshold: Threshold) -> None:
        self.settings.slip_angle = threshold
        save_settings(self.settings)

    def on_yaw_rate_change(self, threshold: Threshold) -> None:
        self.settings.yaw_rate = threshold
        save_settings(self.settings)

    def render(self, _: float) -> None:
        snapshot = read_snapshot()

        bar_size = Size(270, 20)
        guidance_bar(Position(85, 55), bar_size, Color.purple, Color.amber)
        guidance_bar(Position(85, 295), bar_size, Color.white, Color.white)
        guidance_bar(Position(85, 485), bar_size, Color.red, Color.red)

        fl, fr, rl, rr = snapshot.wheels
        marker(Position(85, 92), Size(270, 2), fl.slip_ratio, 0.125)
        marker(Position(85, 108), Size(270, 2), fr.slip_ratio, 0.125)
        marker(Position(85, 124), Size(270, 2), rl.slip_ratio, 0.125)
        marker(Position(85, 140), Size(270, 2), rr.slip_ratio, 0.125)

        marker(Position(85, 332), Size(270, 2), fl.slip_angle, 12.5)
        marker(Position(85, 348), Size(270, 2), fr.slip_angle, 12.5)
        marker(Position(85, 364), Size(270, 2), rl.slip_angle, 12.5)
        marker(Position(85, 380), Size(270, 2), rr.slip_angle, 12.5)

        marker(Position(85, 522), Size(270, 2), snapshot.angular_velocity.yaw, 1.25)

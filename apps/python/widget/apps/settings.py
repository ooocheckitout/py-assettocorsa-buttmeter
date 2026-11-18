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


class SettingsApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        self.id = ac.newApp("AlligatorRacing_Settings")

        ac.setSize(self.id, 365, 485)

        self.listeners = []

        self.threshold_steppers(Position(10, 160), "Lock", self.settings.lock, self.on_lock_change)
        self.threshold_steppers(Position(10, 210), "Spin", self.settings.spin, self.on_spin_change)

        # AC does not hold a reference to callbacks, so keep the bound method alive
        self.callback = self.render
        ac.addRenderCallback(self.id, self.callback)

    def threshold_steppers(self, position: Position, title: str, threshold: Threshold, on_change: object) -> None:
        label = ac.addLabel(self.id, title)
        ac.setPosition(label, position.x, position.y + 1)
        ac.setSize(label, 75, 16)
        ac.setFontSize(label, 14)
        ac.setFontAlignment(label, "left")

        def on_start_change(value: float) -> None:
            threshold.start = value
            on_change(threshold)

        def on_end_change(value: float) -> None:
            threshold.end = value
            on_change(threshold)

        self.stepper(Position(position.x + 75, position.y), "start", threshold.start, on_start_change)
        self.stepper(Position(position.x + 245, position.y), "end", threshold.end, on_end_change)

    def stepper(
        self,
        position: Position,
        title: str,
        value: float,
        on_change: object,
        step: float = 0.01,
        format: str = "{:.2f}",
    ) -> None:
        title_label = ac.addLabel(self.id, title)
        ac.setPosition(title_label, position.x, position.y - 18)
        ac.setSize(title_label, 100, 20)
        ac.setFontSize(title_label, 12)
        ac.setFontAlignment(title_label, "center")

        value_label = ac.addLabel(self.id, format.format(value))
        ac.setPosition(value_label, position.x + 20, position.y)
        ac.setSize(value_label, 60, 20)
        ac.setFontSize(value_label, 14)
        ac.setFontAlignment(value_label, "center")

        def change(delta: float) -> None:
            nonlocal value
            value = round(value + delta, 2)
            on_change(value)
            ac.setText(value_label, format.format(value))

        on_minus = lambda x, y: change(-step)
        on_plus = lambda x, y: change(step)

        button_size = Size(20, 20)

        minus = ac.addButton(self.id, "-")
        ac.setPosition(minus, position.x, position.y)
        ac.setSize(minus, button_size.width, button_size.height)
        ac.addOnClickedListener(minus, on_minus)

        plus = ac.addButton(self.id, "+")
        ac.setPosition(plus, position.x + 80, position.y)
        ac.setSize(plus, button_size.width, button_size.height)
        ac.addOnClickedListener(plus, on_plus)

        self.listeners.extend((on_minus, on_plus))

    def on_lock_change(self, threshold: Threshold) -> None:
        self.settings.lock = threshold
        save_settings(self.settings)

    def on_spin_change(self, threshold: Threshold) -> None:
        self.settings.spin = threshold
        save_settings(self.settings)

    def layout(self, snapshot: Snapshot) -> None:
        bar_size = Size(270, 20)
        guidance_bar(Position(85, 40), bar_size, Color.purple, Color.amber)
        guidance_bar(Position(85, 260), bar_size, Color.white, Color.white)
        guidance_bar(Position(85, 430), bar_size, Color.red, Color.red)

        fl, fr, rl, rr = snapshot.wheels
        marker(Position(85, 77), Size(270, 2), fl.slip_ratio, 0.125)
        marker(Position(85, 93), Size(270, 2), fr.slip_ratio, 0.125)
        marker(Position(85, 109), Size(270, 2), rl.slip_ratio, 0.125)
        marker(Position(85, 125), Size(270, 2), rr.slip_ratio, 0.125)

        marker(Position(85, 297), Size(270, 2), fl.slip_angle, 12.5)
        marker(Position(85, 313), Size(270, 2), fr.slip_angle, 12.5)
        marker(Position(85, 329), Size(270, 2), rl.slip_angle, 12.5)
        marker(Position(85, 345), Size(270, 2), rr.slip_angle, 12.5)

        marker(Position(85, 467), Size(270, 2), snapshot.angular_velocity.yaw, 1.25)

    def render(self, _: float) -> None:
        snapshot = read_snapshot()
        self.layout(snapshot)

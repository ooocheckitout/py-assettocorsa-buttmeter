import ac, acsys

from components.gauge_component import Gauge, GaugeComponent
from render import Color, Position, Size, Slot
from settings import Settings
from telemetry import Snapshot, read_snapshot


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def slip_ratio_bar(position: Position, size: Size) -> None:
    # purple gradient bar
    ac.glColor4f(0.6, 0.3, 1.0, 1)
    ac.glQuad(position.x, position.y, size.width * 0.1, size.height)
    ac.glBegin(acsys.GL.Quads)
    ac.glVertex2f(position.x + size.width * 0.1, position.y)
    ac.glVertex2f(position.x + size.width * 0.1, position.y + size.height)
    ac.glColor4f(0.25, 0.25, 0.25, 0.8)
    ac.glVertex2f(position.x + size.width * 0.3, position.y + size.height)
    ac.glVertex2f(position.x + size.width * 0.3, position.y)
    ac.glEnd()

    # grey bar
    ac.glQuad(position.x + size.width * 0.3, position.y, size.width * 0.4, size.height)

    # amber gradient bar
    ac.glBegin(acsys.GL.Quads)
    ac.glVertex2f(position.x + size.width * 0.7, position.y)
    ac.glVertex2f(position.x + size.width * 0.7, position.y + size.height)
    ac.glColor4f(1.0, 0.69, 0.0, 1)
    ac.glVertex2f(position.x + size.width * 0.9, position.y + size.height)
    ac.glVertex2f(position.x + size.width * 0.9, position.y)
    ac.glEnd()
    ac.glQuad(position.x + size.width * 0.9, position.y, size.width * 0.1, size.height)

    # ticks
    tick_size = Size(1, size.height + 8)
    tick_position = Position(position.x - tick_size.width / 2, position.y - 4)
    
    # fmt: off
    ac.glColor4f(0.9, 0.9, 0.9, 0.85)
    ac.glQuad(tick_position.x + size.width * 0.1, tick_position.y, tick_size.width, tick_size.height)
    ac.glQuad(tick_position.x + size.width * 0.3, tick_position.y, tick_size.width, tick_size.height)
    ac.glQuad(tick_position.x + size.width * 0.7, tick_position.y, tick_size.width, tick_size.height)
    ac.glQuad(tick_position.x + size.width * 0.9, tick_position.y, tick_size.width, tick_size.height)
    # fmt: on


def slip_ratio_line(position: Position, size: Size, ratio: float) -> None:
    # line
    ac.glColor4f(1.0, 1.0, 1.0, 0.15)
    ac.glQuad(position.x, position.y, size.width, size.height)

    # marker
    limit = 0.125
    ac.glColor4f(0.9, 0.9, 0.9, 0.85)
    ac.glQuad(position.x + size.width * (0.5 + clamp(ratio, -limit, limit) * 4) - 2, position.y + size.height / 2 - 6, 4, 12)  # fmt: skip


class SettingsApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        settings = self.settings
        self.id = ac.newApp("AlligatorRacing_Settings")
        self.components = []

        top = 40
        for gauge in (
            Gauge(
                title="Slip ratio",
                names=("FL", "FR", "RL", "RR"),
                read=lambda snapshot: [
                    wheel.slip_ratio for wheel in snapshot.wheels
                ],
                step=0.01,
                digits=2,
                negative=settings.lock,
                positive=settings.spin,
                negative_color=Color.purple,
                positive_color=Color.amber,
                negative_title="Lock",
                positive_title="Spin",
            ),
            Gauge(
                title="Slip angle",
                names=("FL", "FR", "RL", "RR"),
                read=lambda snapshot: [
                    wheel.slip_angle for wheel in snapshot.wheels
                ],
                step=0.5,
                digits=1,
                negative=settings.slip_angle,
                positive=settings.slip_angle,
                negative_color=Color.white,
                positive_color=Color.white,
                negative_title="Limit",
                positive_title="Limit",
            ),
            Gauge(
                title="Yaw rate",
                names=("",),
                read=lambda snapshot: [snapshot.angular_velocity.yaw],
                step=0.05,
                digits=2,
                negative=settings.yaw_rate,
                positive=settings.yaw_rate,
                negative_color=Color.red,
                positive_color=Color.red,
                negative_title="Limit",
                positive_title="Limit",
            ),
        ):
            component = GaugeComponent(self.id, Slot(10, top, 345, 0), gauge, settings)
            self.components.append(component)
            top += component.height

        ac.setSize(self.id, 365, top - 10)
        # AC does not hold a reference to callbacks, so keep the bound method alive
        self.callback = self.render
        ac.addRenderCallback(self.id, self.callback)

    def layout(self, snapshot: Snapshot) -> None:
        slip_ratio_bar(Position(85, 40), Size(270, 20))
        fl, fr, rl, rr = snapshot.wheels
        slip_ratio_line(Position(85, 77), Size(270, 2), fl.slip_ratio)
        slip_ratio_line(Position(85, 93), Size(270, 2), fr.slip_ratio)
        slip_ratio_line(Position(85, 109), Size(270, 2), rl.slip_ratio)
        slip_ratio_line(Position(85, 125), Size(270, 2), rr.slip_ratio)

    def render(self, _: float) -> None:
        snapshot = read_snapshot()
        self.layout(snapshot)
        # for component in self.components:
            # component.update(snapshot)

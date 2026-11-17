import ac, acsys

from render import Color, Position, Size
from settings import Settings, Threshold
from telemetry import Snapshot, read_snapshot


def level(threshold: Threshold, value: float) -> float:
    level = (abs(value) - threshold.start) / (threshold.end - threshold.start)
    return max(0.0, min(level, 1.0))


def draw_arrow(position: Position, size: Size, yaw: float, settings: Settings) -> None:
    third = size.width / 3
    neck = position.y + third * 2

    color = Color.grey.mix(Color.red, level(settings.yaw_rate, yaw))
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x + third, neck, third, position.y + size.height - neck)

    ac.glBegin(acsys.GL.Triangles)
    ac.glVertex2f(position.x, neck)
    ac.glVertex2f(position.x + size.width, neck)
    ac.glVertex2f(position.x + size.width / 2, position.y)
    ac.glEnd()


def draw_tire(position: Position, size: Size, ratio: float, settings: Settings) -> None:
    if ratio < 0:
        color = Color.grey.mix(Color.purple, level(settings.lock, ratio))
    else:
        color = Color.grey.mix(Color.amber, level(settings.spin, ratio))
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x, position.y, size.width, size.height)


def draw_line(position: Position, size: Size, angle: float, settings: Settings) -> None:
    color = Color.grey.mix(Color.white, level(settings.slip_angle, angle))
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x, position.y, size.width, size.height)


class WidgetApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        self.id = ac.newApp("AlligatorRacing_Widget")
        ac.setSize(self.id, 248, 328)
        ac.setTitle(self.id, "")
        ac.setIconPosition(self.id, 0, -10000)
        ac.drawBorder(self.id, 0)

        # AC does not hold a reference to callbacks, so keep the bound method alive
        self.callback = self.render
        ac.addRenderCallback(self.id, self.callback)

    def layout(self, snapshot: Snapshot) -> None:
        fl, fr, rl, rr = snapshot.wheels
        settings = self.settings

        tire_size = Size(64, 104)

        draw_tire(Position(0, 24), tire_size, fl.slip_ratio, settings)
        draw_tire(Position(184, 24), tire_size, fr.slip_ratio, settings)
        draw_tire(Position(0, 200), tire_size, rl.slip_ratio, settings)
        draw_tire(Position(184, 200), tire_size, rr.slip_ratio, settings)

        line_size = Size(64, 8)

        draw_line(Position(0, 8), line_size, fl.slip_angle, settings)
        draw_line(Position(184, 8), line_size, fr.slip_angle, settings)
        draw_line(Position(0, 312), line_size, rl.slip_angle, settings)
        draw_line(Position(184, 312), line_size, rr.slip_angle, settings)

        yaw = snapshot.angular_velocity.yaw
        draw_arrow(Position(104.8, 24), Size(38.4, 280), yaw, settings)

    def render(self, _: float) -> None:
        ac.setBackgroundOpacity(self.id, 0.025)
        snapshot = read_snapshot()
        self.layout(snapshot)

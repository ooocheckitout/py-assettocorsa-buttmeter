import ac, acsys

from render import Color, Position, Size, Slot
from components.rotation_component import RotationComponent
from settings import Settings, Threshold
from telemetry import Snapshot, read_snapshot
from components.tires_component import TireStyle, TiresComponent


def level(threshold: Threshold, value: float) -> float:
    level = (abs(value) - threshold.start) / (threshold.end - threshold.start)
    return max(0.0, min(level, 1.0))


def draw_arrow(position: Position, size: Size, yaw: float, settings: Settings) -> None:
    middle = position.x + size.width / 2
    neck = position.y + 20
    color = Color.grey.mix(Color.red, level(settings.yaw_rate, yaw))
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(middle - 4.5, neck, 9, size.height - 20)
    ac.glBegin(acsys.GL.Triangles)
    ac.glVertex2f(position.x, neck)
    ac.glVertex2f(position.x + size.width, neck)
    ac.glVertex2f(middle, position.y)
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
        settings = self.settings
        self.id = ac.newApp("AlligatorRacing_Widget")
        ac.setSize(self.id, 240, 360)
        ac.setTitle(self.id, "")
        ac.setIconPosition(self.id, 0, -10000)
        ac.drawBorder(self.id, 0)

        self.components = [
            TiresComponent(
                slot=Slot(20, 60, 200, 240),
                track_gap=90,
                axle_gap=70,
                style=TireStyle(
                    line_height=12,
                    line_gap=6,
                    lock=settings.lock,
                    spin=settings.spin,
                    angle=settings.slip_angle,
                    lock_color=Color.purple,
                    spin_color=Color.amber,
                    angle_color=Color.white,
                ),
            ),
            RotationComponent(
                slot=Slot(105, 75, 30, 210),
                length=210,
                thickness=9,
                threshold=settings.yaw_rate,
                color=Color.red,
            ),
        ]
        # AC does not hold a reference to callbacks, so keep the bound method alive
        self.callback = self.render
        ac.addRenderCallback(self.id, self.callback)

    def layout(self, snapshot: Snapshot) -> None:
        fl, fr, rl, rr = snapshot.wheels
        settings = self.settings

        tire_size = Size(70, 110)

        draw_tire(Position(0, 18), tire_size, fl.slip_ratio, settings)
        draw_tire(Position(125, 18), tire_size, fr.slip_ratio, settings)
        draw_tire(Position(0, 185), tire_size, rl.slip_ratio, settings)
        draw_tire(Position(125, 185), tire_size, rr.slip_ratio, settings)

        line_size = Size(70, 10)

        draw_line(Position(0, 0), line_size, fl.slip_angle, settings)
        draw_line(Position(125, 0), line_size, fr.slip_angle, settings)
        draw_line(Position(0, 301), line_size, rl.slip_angle, settings)
        draw_line(Position(125, 301), line_size, rr.slip_angle, settings)

        draw_arrow(Position(83, 0), Size(29, 311), snapshot.angular_velocity.yaw, settings)

    def render(self, _: float) -> None:
        ac.setBackgroundOpacity(self.id, 0.025)
        snapshot = read_snapshot()
        self.layout(snapshot)
        # for component in self.components:
        #     component.update(snapshot)

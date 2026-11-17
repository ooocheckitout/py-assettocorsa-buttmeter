import ac

from render import Color, Slot
from components.rotation_component import RotationComponent
from settings import Settings
from telemetry import read_snapshot
from components.tires_component import TireStyle, TiresComponent


class WidgetApplication:
    def __init__(self, settings: Settings) -> None:
        self.id = ac.newApp("widget")
        ac.setSize(self.id, 240, 360)
        ac.setTitle(self.id, "")
        ac.setIconPosition(self.id, 0, -10000)
        ac.setBackgroundOpacity(self.id, 0.025)
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

    def render(self, _: float) -> None:
        snapshot = read_snapshot()
        for component in self.components:
            component.update(snapshot)

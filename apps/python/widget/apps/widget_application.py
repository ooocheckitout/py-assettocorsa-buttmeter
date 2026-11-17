from application import Application
from render import Color, Slot
from rotation_component import RotationComponent
from settings import Settings
from tires_component import TireStyle, TiresComponent


class WidgetApplication(Application):
    def __init__(self, settings: Settings) -> None:
        super().__init__("widget")
        self.resize(240, 360)
        self.frameless(0.025)

        self.add(
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
            )
        )
        self.add(
            RotationComponent(
                slot=Slot(105, 75, 30, 210),
                length=210,
                thickness=9,
                threshold=settings.yaw_rate,
                color=Color.red,
            )
        )

from application import Application
from gauge_component import Gauge, GaugeComponent
from render import Color, Slot
from settings import Settings


class SettingsApplication(Application):
    def __init__(self, settings: Settings) -> None:
        super().__init__("widget settings")

        top = 40
        for gauge in (
            Gauge(
                title="Slip ratio",
                names=("FL", "FR", "RL", "RR"),
                read=lambda snapshot: [
                    wheel.slip_ratio for wheel in snapshot.ordered_wheels()
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
                    wheel.slip_angle for wheel in snapshot.ordered_wheels()
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
            component = self.add(
                GaugeComponent(self.id, Slot(10, top, 345, 0), gauge, settings)
            )
            top += component.height

        self.resize(365, top - 10)

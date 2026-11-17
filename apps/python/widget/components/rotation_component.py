from render import Color, Component, Point, Slot
from settings import Threshold
from telemetry import Snapshot


class RotationComponent(Component):
    def __init__(
        self,
        slot: Slot,
        length: float,
        thickness: float,
        threshold: Threshold,
        color: Color,
    ) -> None:
        self.threshold = threshold
        self.color = color
        middle = slot.left + slot.width / 2
        top = slot.top + (slot.height - length) / 2
        head = thickness * 2.2
        spread = thickness * 1.6
        neck = top + head
        self.shaft = Slot(middle - thickness / 2, neck, thickness, length - head)
        self.arrow = [
            Point(middle - spread, neck),
            Point(middle + spread, neck),
            Point(middle, top),
        ]

    def update(self, snapshot: Snapshot) -> None:
        color = self.shade(self.threshold, self.color, snapshot.angular_velocity.yaw)
        self.fill(self.shaft, color)
        self.triangle(self.arrow, color)

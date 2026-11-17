from render import Color, Component, Slot
from settings import Threshold
from telemetry import Snapshot


class TireStyle:
    def __init__(
        self,
        line_height: float,
        line_gap: float,
        lock: Threshold,
        spin: Threshold,
        angle: Threshold,
        lock_color: Color,
        spin_color: Color,
        angle_color: Color,
    ) -> None:
        self.line_height = line_height
        self.line_gap = line_gap
        self.lock = lock
        self.spin = spin
        self.angle = angle
        self.lock_color = lock_color
        self.spin_color = spin_color
        self.angle_color = angle_color


class TiresComponent(Component):
    def __init__(
        self, slot: Slot, track_gap: float, axle_gap: float, style: TireStyle
    ) -> None:
        self.style = style
        self.tires = self.grid(slot, 2, 2, track_gap, axle_gap)
        front_left, front_right, rear_left, rear_right = self.tires

        above_offset = -style.line_gap - style.line_height
        below_offset = rear_left.height + style.line_gap

        self.lines = [
            Slot(
                front_left.left,
                front_left.top + above_offset,
                front_left.width,
                style.line_height,
            ),
            Slot(
                front_right.left,
                front_right.top + above_offset,
                front_right.width,
                style.line_height,
            ),
            Slot(
                rear_left.left,
                rear_left.top + below_offset,
                rear_left.width,
                style.line_height,
            ),
            Slot(
                rear_right.left,
                rear_right.top + below_offset,
                rear_right.width,
                style.line_height,
            ),
        ]

    def update(self, snapshot: Snapshot) -> None:
        metrics = (
            snapshot.wheels.front_left,
            snapshot.wheels.front_right,
            snapshot.wheels.rear_left,
            snapshot.wheels.rear_right,
        )

        style = self.style

        for tire, wheel in zip(self.tires, metrics):
            color = self.shade(style.spin, style.spin_color, wheel.slip_ratio)

            if wheel.slip_ratio < 0:
                color = self.shade(style.lock, style.lock_color, wheel.slip_ratio)

            self.fill(tire, color)

        for line, wheel in zip(self.lines, metrics):
            self.fill(line, self.shade(style.angle, style.angle_color, wheel.slip_angle))

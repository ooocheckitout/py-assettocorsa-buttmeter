import ac, acsys
import math

from abc import ABCMeta, abstractmethod

# The app should be installed to: apps\python\{self.name}\{self.name}.py
# The icon is taken from: content\gui\icons\{self.name}_{ON,OFF}.png
# The logs are stored: Documents\Assetto Corsa\logs\py_log.txt


class Wheel:
    def __init__(self, slip_ratio: float, slip_angle: float) -> None:
        self.slip_ratio = slip_ratio
        self.slip_angle = slip_angle


class Wheels:
    def __init__(self, fl: Wheel, fr: Wheel, rl: Wheel, rr: Wheel) -> None:
        self.front_left = fl
        self.front_right = fr
        self.rear_left = rl
        self.rear_right = rr


class Rotation:
    def __init__(self, pitch: float, yaw: float, roll: float) -> None:
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll


class Snapshot:
    def __init__(
        self, speed: float, wheels: Wheels, angular_velocity: Rotation
    ) -> None:
        self.speed = speed
        self.wheels = wheels
        self.angular_velocity = angular_velocity


def read_snapshot() -> Snapshot:
    car = ac.getFocusedCar()
    speed = ac.getCarState(car, acsys.CS.SpeedKMH)

    ratios = ac.getCarState(car, acsys.CS.SlipRatio)
    angles = ac.getCarState(car, acsys.CS.SlipAngle)
    wheels = Wheels(*[Wheel(ratio, angle) for ratio, angle in zip(ratios, angles)])

    pitch, yaw, roll = ac.getCarState(car, acsys.CS.LocalAngularVelocity)
    rotation = Rotation(pitch, yaw, roll)

    return Snapshot(speed, wheels, rotation)


class Color:
    def __init__(self, red: float, green: float, blue: float) -> None:
        self.red = red
        self.green = green
        self.blue = blue


Color.grey = Color(0.2, 0.2, 0.2)
Color.red = Color(1.0, 0.0, 0.0)
Color.purple = Color(0.6, 0.0, 1.0)
Color.amber = Color(1.0, 0.75, 0.0)
Color.white = Color(1.0, 1.0, 1.0)


class Threshold:
    def __init__(
        self, start: float, end: float, start_color: Color, end_color: Color
    ) -> None:
        self.start = start
        self.end = end
        self.start_color = start_color
        self.end_color = end_color


def intensity(value: float, threshold: Threshold) -> float:
    span = threshold.end - threshold.start
    return max(0.0, min((abs(value) - threshold.start) / span, 1.0))


def mix(low: float, high: float, level: float) -> float:
    return low + (high - low) * level


def indicator_color(value: float, threshold: Threshold) -> None:
    level = intensity(value, threshold)
    low = threshold.start_color
    high = threshold.end_color
    ac.glColor4f(
        mix(low.red, high.red, level),
        mix(low.green, high.green, level),
        mix(low.blue, high.blue, level),
        1.0,
    )


class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class Slot:
    def __init__(self, left: float, top: float, width: float, height: float) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height


def draw_shape(mode: int, points: list) -> None:
    ac.glBegin(mode)
    for point in points:
        ac.glVertex2f(point.x, point.y)
    ac.glEnd()


class Component(metaclass=ABCMeta):
    @abstractmethod
    def update(self, snapshot: Snapshot) -> None:
        pass

    @staticmethod
    def fill(slot: Slot, value: float, threshold: Threshold) -> None:
        indicator_color(value, threshold)
        ac.glQuad(slot.left, slot.top, slot.width, slot.height)

    @staticmethod
    def equal(total: float, count: int, gap: float) -> list:
        return [(total - gap * (count - 1)) / count] * count

    @staticmethod
    def stack(area: Slot, heights: list, gap: float) -> list:
        slots = []
        top = area.top
        for height in heights:
            slots.append(Slot(area.left, top, area.width, height))
            top += height + gap
        return slots

    @staticmethod
    def row(area: Slot, widths: list, gap: float) -> list:
        slots = []
        left = area.left
        for width in widths:
            slots.append(Slot(left, area.top, width, area.height))
            left += width + gap
        return slots


class TireStyle:
    def __init__(
        self,
        line: float,
        spacing: float,
        lock_threshold: Threshold,
        spin_threshold: Threshold,
        angle_threshold: Threshold,
    ) -> None:
        self.line = line
        self.spacing = spacing
        self.lock_threshold = lock_threshold
        self.spin_threshold = spin_threshold
        self.angle_threshold = angle_threshold


class TiresComponent(Component):
    def __init__(self, slot: Slot, gap: float, style: TireStyle) -> None:
        self.slot = slot
        self.gap = gap
        self.style = style

    def draw_tire(self, slot: Slot, wheel: Wheel, line_below: bool) -> None:
        style = self.style
        ratio_threshold = (
            style.lock_threshold if wheel.slip_ratio < 0 else style.spin_threshold
        )
        self.fill(slot, wheel.slip_ratio, ratio_threshold)
        line_top = (
            slot.top + slot.height + style.spacing
            if line_below
            else slot.top - style.spacing - style.line
        )
        line_slot = Slot(slot.left, line_top, slot.width, style.line)
        self.fill(line_slot, wheel.slip_angle, style.angle_threshold)

    def update(self, snapshot: Snapshot) -> None:
        wheels = snapshot.wheels
        gap = self.gap
        front, rear = self.stack(self.slot, self.equal(self.slot.height, 2, gap), gap)
        front_left, front_right = self.row(front, self.equal(front.width, 2, gap), gap)
        rear_left, rear_right = self.row(rear, self.equal(rear.width, 2, gap), gap)
        self.draw_tire(front_left, wheels.front_left, False)
        self.draw_tire(front_right, wheels.front_right, False)
        self.draw_tire(rear_left, wheels.rear_left, True)
        self.draw_tire(rear_right, wheels.rear_right, True)


class RotationComponent(Component):
    def __init__(
        self,
        slot: Slot,
        length: float,
        thickness: float,
        dash: float,
        threshold: Threshold,
    ) -> None:
        self.slot = slot
        self.length = length
        self.thickness = thickness
        self.dash = dash
        self.threshold = threshold

    def draw_center_line(self, middle: float) -> None:
        ac.glColor4f(0.5, 0.5, 0.5, 1.0)
        bottom = self.slot.top + self.slot.height
        for index in range(math.ceil(self.slot.height / (2 * self.dash))):
            dash_top = self.slot.top + index * 2 * self.dash
            height = min(self.dash, bottom - dash_top)
            ac.glQuad(middle - 1, dash_top, 2, height)

    def update(self, snapshot: Snapshot) -> None:
        middle = self.slot.left + self.slot.width / 2
        self.draw_center_line(middle)

        indicator_color(snapshot.angular_velocity.yaw, self.threshold)

        top = self.slot.top + (self.slot.height - self.length) / 2
        head = self.thickness * 3
        neck = top + head
        ac.glQuad(
            middle - self.thickness / 2,
            neck,
            self.thickness,
            self.length - head,
        )
        draw_shape(
            acsys.GL.Triangles,
            [
                Point(middle - head / 2, neck),
                Point(middle + head / 2, neck),
                Point(middle, top),
            ],
        )


components = ()


def render_all(_: float) -> None:
    """Runs on every frame after window is drawn."""
    snapshot = read_snapshot()

    for component in components:
        component.update(snapshot)


def acMain(_: str) -> str:
    """Runs once the session is loaded."""
    global components

    name = "widget"
    app_id = ac.newApp(name)

    ac.setSize(app_id, 600, 800)

    components = (
        TiresComponent(
            slot=Slot(250, 40, 160, 220),
            gap=40,
            style=TireStyle(
                line=12,
                spacing=6,
                lock_threshold=Threshold(0.10, 0.20, Color.grey, Color.purple),
                spin_threshold=Threshold(0.10, 0.20, Color.grey, Color.amber),
                angle_threshold=Threshold(6.0, 10.0, Color.grey, Color.white),
            ),
        ),
        RotationComponent(
            slot=Slot(315, 30, 30, 240),
            length=180,
            thickness=10,
            dash=8,
            threshold=Threshold(0.2, 0.6, Color.grey, Color.red),
        ),
    )

    ac.addRenderCallback(app_id, render_all)

    return name

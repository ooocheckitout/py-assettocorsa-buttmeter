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


def axis_bar(
    left: float,
    top: float,
    width: float,
    height: float,
    value: float,
    threshold: Threshold,
) -> None:
    indicator_color(0.0, threshold)
    ac.glQuad(left, top, width, height)
    if intensity(value, threshold) == 0.0:
        return
    indicator_color(value, threshold)
    if width >= height:
        half = width / 2
        ac.glQuad(left + half if value > 0 else left, top, half, height)
    else:
        half = height / 2
        ac.glQuad(left, top + half if value > 0 else top, width, half)


class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def draw_shape(mode: int, points: list) -> None:
    ac.glBegin(mode)
    for point in points:
        ac.glVertex2f(point.x, point.y)
    ac.glEnd()


class Component(metaclass=ABCMeta):
    @abstractmethod
    def update(self, snapshot: Snapshot) -> None:
        pass


class RotationRateComponent(Component):
    def __init__(
        self,
        left: float,
        top: float,
        width: float,
        height: float,
        gap: float,
        threshold: Threshold,
    ) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.gap = gap
        self.threshold = threshold

    def update(self, snapshot: Snapshot) -> None:
        rotation = snapshot.angular_velocity
        axes = (rotation.pitch, rotation.yaw, rotation.roll)
        step = self.height + self.gap
        for row, value in enumerate(axes):
            bar_top = self.top + row * step
            axis_bar(
                self.left, bar_top, self.width, self.height, value, self.threshold
            )


class TireStateComponent(Component):
    def __init__(
        self,
        left: float,
        top: float,
        width: float,
        height: float,
        gap: float,
        line: float,
        spacing: float,
        lock_threshold: Threshold,
        spin_threshold: Threshold,
        angle_threshold: Threshold,
    ) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.gap = gap
        self.line = line
        self.spacing = spacing
        self.lock_threshold = lock_threshold
        self.spin_threshold = spin_threshold
        self.angle_threshold = angle_threshold

    def update(self, snapshot: Snapshot) -> None:
        cells = (
            (0, 0, snapshot.wheels.front_left),
            (1, 0, snapshot.wheels.front_right),
            (0, 1, snapshot.wheels.rear_left),
            (1, 1, snapshot.wheels.rear_right),
        )
        for column, row, wheel in cells:
            left = self.left + column * (self.width + self.gap)
            top = self.top + row * (self.height + self.gap)
            ratio_threshold = (
                self.lock_threshold if wheel.slip_ratio < 0 else self.spin_threshold
            )
            indicator_color(wheel.slip_ratio, ratio_threshold)
            ac.glQuad(left, top, self.width, self.height)
            line_top = (
                top - self.spacing - self.line
                if row == 0
                else top + self.height + self.spacing
            )
            indicator_color(wheel.slip_angle, self.angle_threshold)
            ac.glQuad(left, line_top, self.width, self.line)


class BalanceComponent(Component):
    def __init__(
        self,
        center: Point,
        length: float,
        line_length: float,
        thickness: float,
        dash: float,
        threshold: Threshold,
    ) -> None:
        self.center = center
        self.length = length
        self.line_length = line_length
        self.thickness = thickness
        self.dash = dash
        self.threshold = threshold

    def draw_center_line(self) -> None:
        ac.glColor4f(0.5, 0.5, 0.5, 1.0)
        top = self.center.y - self.line_length / 2
        bottom = top + self.line_length
        for index in range(math.ceil(self.line_length / (2 * self.dash))):
            dash_top = top + index * 2 * self.dash
            height = min(self.dash, bottom - dash_top)
            ac.glQuad(self.center.x - 1, dash_top, 2, height)

    def update(self, snapshot: Snapshot) -> None:
        self.draw_center_line()

        indicator_color(snapshot.angular_velocity.yaw, self.threshold)

        top = self.center.y - self.length / 2
        head = self.thickness * 3
        neck = top + head
        ac.glQuad(
            self.center.x - self.thickness / 2,
            neck,
            self.thickness,
            self.length - head,
        )
        draw_shape(
            acsys.GL.Triangles,
            [
                Point(self.center.x - head / 2, neck),
                Point(self.center.x + head / 2, neck),
                Point(self.center.x, top),
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

    gray = Color(0.2, 0.2, 0.2)
    red = Color(1.0, 0.0, 0.0)
    purple = Color(0.6, 0.0, 1.0)
    amber = Color(1.0, 0.75, 0.0)
    white = Color(1.0, 1.0, 1.0)

    components = (
        RotationRateComponent(
            left=10,
            top=460,
            width=190,
            height=40,
            gap=10,
            threshold=Threshold(0.6, 1.2, gray, red),
        ),
        TireStateComponent(
            left=250,
            top=40,
            width=60,
            height=90,
            gap=40,
            line=12,
            spacing=6,
            lock_threshold=Threshold(0.10, 0.20, gray, purple),
            spin_threshold=Threshold(0.10, 0.20, gray, amber),
            angle_threshold=Threshold(6.0, 10.0, gray, white),
        ),
        BalanceComponent(
            center=Point(330, 150),
            length=180,
            line_length=240,
            thickness=10,
            dash=8,
            threshold=Threshold(0.2, 0.6, gray, red),
        ),
    )

    ac.addRenderCallback(app_id, render_all)

    return name

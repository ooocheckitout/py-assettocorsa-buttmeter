import ac, acsys

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


class Threshold:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


def intensity(value: float, threshold: Threshold) -> float:
    span = threshold.end - threshold.start
    return max(0.0, min((abs(value) - threshold.start) / span, 1.0))


def indicator_color(level: float) -> None:
    if level == 0.0:
        ac.glColor4f(0.2, 0.2, 0.2, 1.0)
    else:
        ac.glColor4f(1.0, 0.8 * (1.0 - level), 0.0, 1.0)


class Component(metaclass=ABCMeta):
    @abstractmethod
    def update(self, snapshot: Snapshot) -> None:
        pass


class SlipRatioComponent(Component):
    def __init__(
        self, left: float, top: float, size: float, gap: float, threshold: Threshold
    ) -> None:
        self.left = left
        self.top = top
        self.size = size
        self.gap = gap
        self.threshold = threshold

    def update(self, snapshot: Snapshot) -> None:
        cells = (
            (0, 0, snapshot.wheels.front_left),
            (1, 0, snapshot.wheels.front_right),
            (0, 1, snapshot.wheels.rear_left),
            (1, 1, snapshot.wheels.rear_right),
        )
        step = self.size + self.gap
        for column, row, wheel in cells:
            indicator_color(intensity(wheel.slip_ratio, self.threshold))
            ac.glQuad(
                self.left + column * step, self.top + row * step, self.size, self.size
            )


class SlipAngleComponent(Component):
    def __init__(
        self, left: float, top: float, size: float, gap: float, threshold: Threshold
    ) -> None:
        self.left = left
        self.top = top
        self.size = size
        self.gap = gap
        self.threshold = threshold

    def update(self, snapshot: Snapshot) -> None:
        cells = (
            (0, 0, snapshot.wheels.front_left),
            (1, 0, snapshot.wheels.front_right),
            (0, 1, snapshot.wheels.rear_left),
            (1, 1, snapshot.wheels.rear_right),
        )
        step = self.size + self.gap
        for column, row, wheel in cells:
            indicator_color(intensity(wheel.slip_ratio, self.threshold))
            ac.glQuad(
                self.left + column * step, self.top + row * step, self.size, self.size
            )


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
        half = self.width / 2
        for row, value in enumerate(axes):
            bar_top = self.top + row * step
            level = intensity(value, self.threshold)
            indicator_color(0.0)
            ac.glQuad(self.left, bar_top, self.width, self.height)
            if level > 0.0:
                indicator_color(level)
                bar_left = self.left + half if value > 0 else self.left
                ac.glQuad(bar_left, bar_top, half, self.height)


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
        ratio_threshold: Threshold,
        angle_threshold: Threshold,
    ) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.gap = gap
        self.line = line
        self.spacing = spacing
        self.ratio_threshold = ratio_threshold
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
            indicator_color(intensity(wheel.slip_ratio, self.ratio_threshold))
            ac.glQuad(left, top, self.width, self.height)
            line_top = (
                top - self.spacing - self.line
                if row == 0
                else top + self.height + self.spacing
            )
            indicator_color(intensity(wheel.slip_angle, self.angle_threshold))
            ac.glQuad(left, line_top, self.width, self.line)


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
        SlipRatioComponent(
            left=10, top=40, size=90, gap=10, threshold=Threshold(0.10, 0.20)
        ),
        SlipAngleComponent(
            left=10, top=250, size=90, gap=10, threshold=Threshold(6.0, 10.0)
        ),
        RotationRateComponent(
            left=10,
            top=460,
            width=190,
            height=40,
            gap=10,
            threshold=Threshold(0.6, 1.2),
        ),
        TireStateComponent(
            left=250,
            top=40,
            width=60,
            height=90,
            gap=40,
            line=12,
            spacing=6,
            ratio_threshold=Threshold(0.10, 0.20),
            angle_threshold=Threshold(6.0, 10.0),
        ),
    )

    ac.addRenderCallback(app_id, render_all)

    return name

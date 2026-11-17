import math

import ac, acsys

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


class Component:
    def update(self, snapshot: Snapshot) -> None:
        pass


class SlipRatioComponent(Component):
    def __init__(
        self, left: float, top: float, size: float, gap: float, limit: float
    ) -> None:
        self.left = left
        self.top = top
        self.size = size
        self.gap = gap
        self.limit = limit

    def update(self, snapshot: Snapshot) -> None:
        cells = (
            (0, 0, snapshot.wheels.front_left),
            (1, 0, snapshot.wheels.front_right),
            (0, 1, snapshot.wheels.rear_left),
            (1, 1, snapshot.wheels.rear_right),
        )
        step = self.size + self.gap
        for column, row, wheel in cells:
            level = min(abs(wheel.slip_ratio) / self.limit, 1.0)
            ac.glColor4f(level, 1.0 - level, 0.0, 1.0)
            ac.glQuad(
                self.left + column * step, self.top + row * step, self.size, self.size
            )


class SlipAngleComponent(Component):
    def __init__(
        self, left: float, top: float, size: float, gap: float, limit: float
    ) -> None:
        self.left = left
        self.top = top
        self.size = size
        self.gap = gap
        self.limit = limit

    def update(self, snapshot: Snapshot) -> None:
        cells = (
            (0, 0, snapshot.wheels.front_left),
            (1, 0, snapshot.wheels.front_right),
            (0, 1, snapshot.wheels.rear_left),
            (1, 1, snapshot.wheels.rear_right),
        )
        step = self.size + self.gap
        half = self.size / 2
        for column, row, wheel in cells:
            cell_left = self.left + column * step
            cell_top = self.top + row * step
            ratio = max(-1.0, min(wheel.slip_angle / self.limit, 1.0))
            level = abs(ratio)
            offset = ratio * half

            ac.glColor4f(0.2, 0.2, 0.2, 1.0)
            ac.glQuad(cell_left, cell_top, self.size, self.size)

            ac.glColor4f(level, 1.0 - level, 0.0, 1.0)
            ac.glQuad(
                cell_left + half + min(offset, 0.0), cell_top, abs(offset), self.size
            )


class RotationRateComponent(Component):
    def __init__(
        self,
        left: float,
        top: float,
        width: float,
        height: float,
        gap: float,
        limit: float,
    ) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.gap = gap
        self.limit = limit

    def update(self, snapshot: Snapshot) -> None:
        rotation = snapshot.angular_velocity
        axes = (rotation.pitch, rotation.yaw, rotation.roll)
        step = self.height + self.gap
        half = self.width / 2
        for row, value in enumerate(axes):
            bar_top = self.top + row * step
            ratio = max(-1.0, min(value / self.limit, 1.0))
            level = abs(ratio)
            offset = ratio * half

            ac.glColor4f(0.2, 0.2, 0.2, 1.0)
            ac.glQuad(self.left, bar_top, self.width, self.height)

            ac.glColor4f(level, 1.0 - level, 0.0, 1.0)
            ac.glQuad(
                self.left + half + min(offset, 0.0), bar_top, abs(offset), self.height
            )


class FrictionCircleComponent(Component):
    def __init__(
        self,
        left: float,
        top: float,
        size: float,
        gap: float,
        ratio_limit: float,
        angle_limit: float,
    ) -> None:
        self.left = left
        self.top = top
        self.size = size
        self.gap = gap
        self.ratio_limit = ratio_limit
        self.angle_limit = angle_limit

    def update(self, snapshot: Snapshot) -> None:
        cells = (
            (0, 0, snapshot.wheels.front_left),
            (1, 0, snapshot.wheels.front_right),
            (0, 1, snapshot.wheels.rear_left),
            (1, 1, snapshot.wheels.rear_right),
        )
        step = self.size + self.gap
        half = self.size / 2
        radius = half * 0.7
        dot = self.size * 0.08
        for column, row, wheel in cells:
            center_x = self.left + column * step + half
            center_y = self.top + row * step + half
            lateral = wheel.slip_angle / self.angle_limit
            longitudinal = wheel.slip_ratio / self.ratio_limit
            usage = math.hypot(lateral, longitudinal)
            scale = min(usage, half / radius) / usage if usage > 0 else 0.0
            level = min(usage, 1.0)

            ac.glColor4f(0.2, 0.2, 0.2, 1.0)
            ac.glQuad(center_x - half, center_y - half, self.size, self.size)

            draw_ring(center_x, center_y, radius)

            ac.glColor4f(level, 1.0 - level, 0.0, 1.0)
            ac.glQuad(
                center_x + lateral * scale * radius - dot / 2,
                center_y - longitudinal * scale * radius - dot / 2,
                dot,
                dot,
            )


def draw_ring(center_x: float, center_y: float, radius: float) -> None:
    segments = 32
    ac.glColor4f(0.6, 0.6, 0.6, 1.0)
    ac.glBegin(acsys.GL.LineStrip)
    for index in range(segments + 1):
        angle = 2 * math.pi * index / segments
        ac.glVertex2f(
            center_x + math.cos(angle) * radius, center_y + math.sin(angle) * radius
        )
    ac.glEnd()


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
        SlipRatioComponent(left=10, top=40, size=90, gap=10, limit=0.2),
        SlipAngleComponent(left=10, top=250, size=90, gap=10, limit=8.0),
        RotationRateComponent(
            left=10, top=460, width=190, height=40, gap=10, limit=1.0
        ),
        FrictionCircleComponent(
            left=220, top=40, size=190, gap=10, ratio_limit=0.15, angle_limit=8.0
        ),
    )

    ac.addRenderCallback(app_id, render_all)

    return name

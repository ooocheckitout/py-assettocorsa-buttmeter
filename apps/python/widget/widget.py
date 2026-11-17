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
    ratios = ac.getCarState(car, acsys.CS.SlipRatio)
    angles = ac.getCarState(car, acsys.CS.SlipAngle)
    return Snapshot(
        ac.getCarState(car, acsys.CS.SpeedKMH),
        Wheels(*[Wheel(ratio, angle) for ratio, angle in zip(ratios, angles)]),
        Rotation(*ac.getCarState(car, acsys.CS.LocalAngularVelocity)),
    )


class Color:
    def __init__(
        self, red: float, green: float, blue: float, alpha: float = 1
    ) -> None:
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

    def mix(self, other: "Color", level: float) -> "Color":
        return Color(
            self.red + (other.red - self.red) * level,
            self.green + (other.green - self.green) * level,
            self.blue + (other.blue - self.blue) * level,
            self.alpha + (other.alpha - self.alpha) * level,
        )


Color.grey = Color(0.25, 0.25, 0.25, 0.8)
Color.red = Color(1.0, 0.2, 0.2)
Color.purple = Color(0.6, 0.3, 1.0)
Color.amber = Color(1.0, 0.69, 0.0)
Color.white = Color(0.9, 0.9, 0.9, 0.85)


class Threshold:
    def __init__(
        self, start: float, end: float, start_color: Color, end_color: Color
    ) -> None:
        self.start = start
        self.end = end
        self.start_color = start_color
        self.end_color = end_color

    def color(self, value: float) -> Color:
        level = (abs(value) - self.start) / (self.end - self.start)
        return self.start_color.mix(self.end_color, max(0.0, min(level, 1.0)))


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


class Component(metaclass=ABCMeta):
    @abstractmethod
    def update(self, snapshot: Snapshot) -> None:
        pass

    @staticmethod
    def paint(color: Color) -> None:
        ac.glColor4f(color.red, color.green, color.blue, color.alpha)

    @staticmethod
    def fill(slot: Slot, color: Color) -> None:
        Component.paint(color)
        ac.glQuad(slot.left, slot.top, slot.width, slot.height)

    @staticmethod
    def triangle(points: list, color: Color) -> None:
        Component.paint(color)
        ac.glBegin(acsys.GL.Triangles)
        for point in points:
            ac.glVertex2f(point.x, point.y)
        ac.glEnd()

    @staticmethod
    def grid(
        area: Slot, columns: int, rows: int, column_gap: float, row_gap: float
    ) -> list:
        width = (area.width - column_gap * (columns - 1)) / columns
        height = (area.height - row_gap * (rows - 1)) / rows

        slots = []

        for row in range(rows):
            for column in range(columns):
                x = area.left + column * (width + column_gap)
                y = area.top + row * (height + row_gap)
                slots.append(Slot(x, y, width, height))

        return slots


class TireStyle:
    def __init__(
        self,
        line_height: float,
        line_gap: float,
        lock_threshold: Threshold,
        spin_threshold: Threshold,
        angle_threshold: Threshold,
    ) -> None:
        self.line_height = line_height
        self.line_gap = line_gap
        self.lock_threshold = lock_threshold
        self.spin_threshold = spin_threshold
        self.angle_threshold = angle_threshold


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

        for tire, wheel in zip(self.tires, metrics):
            threshold = self.style.spin_threshold

            if wheel.slip_ratio < 0:
                threshold = self.style.lock_threshold

            self.fill(tire, threshold.color(wheel.slip_ratio))

        for line, wheel in zip(self.lines, metrics):
            self.fill(line, self.style.angle_threshold.color(wheel.slip_angle))


class RotationComponent(Component):
    def __init__(
        self,
        slot: Slot,
        length: float,
        thickness: float,
        threshold: Threshold,
    ) -> None:
        self.threshold = threshold
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
        color = self.threshold.color(snapshot.angular_velocity.yaw)
        self.fill(self.shaft, color)
        self.triangle(self.arrow, color)


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

    ac.setSize(app_id, 240, 360)
    ac.setTitle(app_id, "")
    ac.setIconPosition(app_id, 0, -10000)
    ac.setBackgroundOpacity(app_id, 0.025)
    ac.drawBorder(app_id, 0)

    components = (
        TiresComponent(
            slot=Slot(20, 60, 200, 240),
            track_gap=90,
            axle_gap=70,
            style=TireStyle(
                line_height=12,
                line_gap=6,
                lock_threshold=Threshold(0.05, 0.10, Color.grey, Color.purple),
                spin_threshold=Threshold(0.05, 0.10, Color.grey, Color.amber),
                angle_threshold=Threshold(6.0, 8.0, Color.grey, Color.white),
            ),
        ),
        RotationComponent(
            slot=Slot(105, 75, 30, 210),
            length=210,
            thickness=9,
            threshold=Threshold(0.2, 0.6, Color.grey, Color.red),
        ),
    )

    ac.addRenderCallback(app_id, render_all)

    return name

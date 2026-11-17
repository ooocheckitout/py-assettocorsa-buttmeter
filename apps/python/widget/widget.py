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
    def __init__(self, red: float, green: float, blue: float) -> None:
        self.red = red
        self.green = green
        self.blue = blue

    def mix(self, other: "Color", level: float) -> "Color":
        return Color(
            self.red + (other.red - self.red) * level,
            self.green + (other.green - self.green) * level,
            self.blue + (other.blue - self.blue) * level,
        )


Color.grey = Color(0.2, 0.2, 0.2)
Color.silver = Color(0.5, 0.5, 0.5)
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
        ac.glColor4f(color.red, color.green, color.blue, 1.0)

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
    def grid(area: Slot, columns: int, rows: int, gap: float) -> list:
        width = (area.width - gap * (columns - 1)) / columns
        height = (area.height - gap * (rows - 1)) / rows

        slots = []

        for row in range(rows):
            for column in range(columns):
                x = area.left + column * (width + gap)
                y = area.top + row * (height + gap)
                slots.append(Slot(x, y, width, height))

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
        ratio = style.lock_threshold if wheel.slip_ratio < 0 else style.spin_threshold
        self.fill(slot, ratio.color(wheel.slip_ratio))
        line_top = (
            slot.top + slot.height + style.spacing
            if line_below
            else slot.top - style.spacing - style.line
        )
        line_slot = Slot(slot.left, line_top, slot.width, style.line)
        self.fill(line_slot, style.angle_threshold.color(wheel.slip_angle))

    def update(self, snapshot: Snapshot) -> None:
        wheels = snapshot.wheels
        (front_left, front_right), (rear_left, rear_right) = self.grid(
            self.slot, 2, 2, self.gap
        )
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
        bottom = self.slot.top + self.slot.height
        dash_top = self.slot.top
        while dash_top < bottom:
            height = min(self.dash, bottom - dash_top)
            self.fill(Slot(middle - 1, dash_top, 2, height), Color.silver)
            dash_top += 2 * self.dash

    def update(self, snapshot: Snapshot) -> None:
        middle = self.slot.left + self.slot.width / 2
        self.draw_center_line(middle)

        color = self.threshold.color(snapshot.angular_velocity.yaw)
        top = self.slot.top + (self.slot.height - self.length) / 2
        head = self.thickness * 3
        neck = top + head
        shaft = Slot(
            middle - self.thickness / 2, neck, self.thickness, self.length - head
        )
        self.fill(shaft, color)
        self.triangle(
            [
                Point(middle - head / 2, neck),
                Point(middle + head / 2, neck),
                Point(middle, top),
            ],
            color,
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

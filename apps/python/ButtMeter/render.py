import ac, acsys

from abc import ABCMeta, abstractmethod

from telemetry import Snapshot


class Color:
    def __init__(self, red: float, green: float, blue: float, alpha: float = 1) -> None:
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

    def brightness(self, alpha: float) -> "Color":
        return Color(self.red, self.green, self.blue, alpha)


Color.grey = Color(0.25, 0.25, 0.25, 0.8)
Color.red = Color(1.0, 0.25, 0.3)
Color.teal = Color(0.2, 0.85, 0.8)
Color.purple = Color(0.6, 0.3, 1.0)
Color.amber = Color(1.0, 0.69, 0.0)
Color.white = Color(0.9, 0.9, 0.9, 0.85)


class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class Position:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class Size:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height


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
    def grid(area: Slot, columns: int, rows: int, column_gap: float, row_gap: float) -> list:
        width = (area.width - column_gap * (columns - 1)) / columns
        height = (area.height - row_gap * (rows - 1)) / rows

        slots = []

        for row in range(rows):
            for column in range(columns):
                x = area.left + column * (width + column_gap)
                y = area.top + row * (height + row_gap)
                slots.append(Slot(x, y, width, height))

        return slots

    @staticmethod
    def label(app_id: int, text: str, slot: Slot, size: float, alignment: str) -> int:
        label = ac.addLabel(app_id, text)
        ac.setPosition(label, slot.left, slot.top)
        ac.setSize(label, slot.width, slot.height)
        ac.setFontSize(label, size)
        ac.setFontAlignment(label, alignment)
        return label

    @staticmethod
    def button(app_id: int, text: str, slot: Slot, on_click: object) -> int:
        button = ac.addButton(app_id, text)
        ac.setPosition(button, slot.left, slot.top)
        ac.setSize(button, slot.width, slot.height)
        ac.addOnClickedListener(button, on_click)
        return button

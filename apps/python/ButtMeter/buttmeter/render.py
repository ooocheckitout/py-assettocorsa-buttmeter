class Color:
    def __init__(self, red: float, green: float, blue: float, alpha: float = 1) -> None:
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

    def __iter__(self):
        return iter((self.red, self.green, self.blue, self.alpha))

    def mix(self, other: "Color", level: float) -> "Color":
        return Color(
            self.red + (other.red - self.red) * level,
            self.green + (other.green - self.green) * level,
            self.blue + (other.blue - self.blue) * level,
            self.alpha + (other.alpha - self.alpha) * level,
        )

    def brightness(self, alpha: float) -> "Color":
        return Color(self.red, self.green, self.blue, alpha)


class KnownColors:
    grey = Color(0.25, 0.25, 0.25, 0.8)
    red = Color(1.0, 0.25, 0.3)
    teal = Color(0.2, 0.85, 0.8)
    purple = Color(0.6, 0.3, 1.0)
    amber = Color(1.0, 0.69, 0.0)
    white = Color(0.9, 0.9, 0.9, 0.85)


class Position:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class Size:
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

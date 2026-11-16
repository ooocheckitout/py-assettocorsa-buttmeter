import ac

GREY = (0.3, 0.3, 0.3, 1.0)
PURPLE = (0.6, 0.3, 1.0, 1.0)
AMBER = (1.0, 0.7, 0.0, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
FAINT = (1.0, 1.0, 1.0, 0.15)


class Bar:
    def __init__(self, left: float, top: float, width: int, height: float, half: float) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.half = half


class ColorRange:
    def __init__(self, start: float, full: float, color_from: tuple, color_to: tuple) -> None:
        self.start = start
        self.full = full
        self.color_from = color_from
        self.color_to = color_to


def blend(color_from: tuple, color_to: tuple, fraction: float) -> tuple:
    return tuple(start + (end - start) * fraction for start, end in zip(color_from, color_to))


def range_fraction(value: float, color_range: ColorRange) -> float:
    width = (color_range.full - color_range.start) or 1e-9
    return max(0.0, min(1.0, (value - color_range.start) / width))


def range_distance(value: float, color_range: ColorRange) -> float:
    low, high = sorted((color_range.start, color_range.full))
    return max(low - value, 0.0, value - high)


def color_at(value: float, color_ranges: list) -> tuple:
    nearest = min(color_ranges, key=lambda color_range: range_distance(value, color_range))
    return blend(nearest.color_from, nearest.color_to, range_fraction(value, nearest))


def column_value(bar: Bar, column: int) -> float:
    return (column + 0.5) / bar.width * 2 * bar.half - bar.half


def value_pixel(bar: Bar, value: float) -> float:
    clamped = max(-bar.half, min(bar.half, value))
    return bar.left + (clamped + bar.half) / (2 * bar.half) * bar.width


def draw_gradient(bar: Bar, color_ranges: list) -> None:
    for column in range(bar.width):
        ac.glColor4f(*color_at(column_value(bar, column), color_ranges))
        ac.glQuad(bar.left + column, bar.top, 1, bar.height)


def draw_tick(bar: Bar, value: float) -> None:
    ac.glColor4f(*WHITE)
    ac.glQuad(value_pixel(bar, value) - 0.5, bar.top - 4, 1, bar.height + 8)


def draw_ticks(bar: Bar, color_ranges: list) -> None:
    draw_tick(bar, 0.0)
    for color_range in color_ranges:
        draw_tick(bar, color_range.start)
        draw_tick(bar, color_range.full)


def draw_marker_row(bar: Bar, top: float, height: float, value: float) -> None:
    ac.glColor4f(*FAINT)
    ac.glQuad(bar.left, top + height / 2 - 1, bar.width, 2)
    ac.glColor4f(*WHITE)
    ac.glQuad(value_pixel(bar, value) - 2, top + 2, 4, height - 4)

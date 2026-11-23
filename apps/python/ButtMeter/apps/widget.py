import ac, acsys

from render import Color, Position, Size
from settings import Settings, Threshold, save_settings
from telemetry import read_snapshot

SCALES = (0.5, 2 / 3, 1.0)


def scale_button(app_id: int, on_click: object) -> int:
    button = ac.addButton(app_id, "")
    ac.drawBorder(button, 0)
    ac.setBackgroundOpacity(button, 0)
    ac.setSize(button, 18, 18)
    ac.addOnClickedListener(button, on_click)
    return button


def draw_corner_arrow(position: Position, size: Size, horizontal: float, vertical: float, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    tip = Position(
        position.x + (size.width if horizontal > 0 else 0),
        position.y + (size.height if vertical > 0 else 0),
    )
    width = -horizontal * size.width
    height = -vertical * size.height

    # arrowhead, tip in the corner the arrow points to
    ac.glBegin(acsys.GL.Triangles)
    ac.glVertex2f(tip.x + width * 0.0556, tip.y + height * 0.0556)
    ac.glVertex2f(tip.x + width * 0.8333, tip.y + height * 0.0556)
    ac.glVertex2f(tip.x + width * 0.0556, tip.y + height * 0.8333)
    ac.glEnd()
    # shaft, from the opposite corner to the neck
    ac.glBegin(acsys.GL.Quads)
    ac.glVertex2f(tip.x + width * 1.0230, tip.y + height * 0.8659)
    ac.glVertex2f(tip.x + width * 0.5230, tip.y + height * 0.3659)
    ac.glVertex2f(tip.x + width * 0.3659, tip.y + height * 0.5230)
    ac.glVertex2f(tip.x + width * 0.8659, tip.y + height * 1.0230)
    ac.glEnd()


def draw_grow_icon(position: Position, color: Color) -> None:
    size = Size(18, 18)
    half = Size(size.width / 2, size.height / 2)
    draw_corner_arrow(position, half, -1, -1, color)
    draw_corner_arrow(Position(position.x + half.width, position.y + half.height), half, 1, 1, color)


def draw_shrink_icon(position: Position, color: Color) -> None:
    size = Size(18, 18)
    half = Size(size.width / 2, size.height / 2)
    draw_corner_arrow(Position(position.x, position.y + half.height), half, 1, -1, color)
    draw_corner_arrow(Position(position.x + half.width, position.y), half, -1, 1, color)


def level(threshold: Threshold, value: float) -> float:
    if threshold.end <= threshold.start:
        return 1.0 if abs(value) >= threshold.start else 0.0
    level = (abs(value) - threshold.start) / (threshold.end - threshold.start)
    return max(0.0, min(level, 1.0))


def draw_line(position: Position, scale: float, angle: float, threshold: Threshold, slide_color: Color) -> None:
    size = Size(64 * scale, 20 * scale)
    color = Color.grey.mix(slide_color, level(threshold, angle))
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    # middle column, full height
    ac.glQuad(position.x + size.width * 0.125, position.y, size.width * 0.75, size.height)
    # left column, between the corners
    ac.glQuad(position.x, position.y + size.width * 0.125, size.width * 0.125, size.height - size.width * 0.25)
    # right column, between the corners
    ac.glQuad(position.x + size.width * 0.875, position.y + size.width * 0.125, size.width * 0.125, size.height - size.width * 0.25)  # fmt: skip

    ac.glBegin(acsys.GL.Quads)
    # top left corner, left edge half
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.width * 0.125)
    ac.glVertex2f(position.x, position.y + size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.0095, position.y + size.width * 0.0772)
    ac.glVertex2f(position.x + size.width * 0.0366, position.y + size.width * 0.0366)
    # top left corner, top edge half
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.0366, position.y + size.width * 0.0366)
    ac.glVertex2f(position.x + size.width * 0.0772, position.y + size.width * 0.0095)
    ac.glVertex2f(position.x + size.width * 0.125, position.y)
    ac.glEnd()

    ac.glBegin(acsys.GL.Quads)
    # top right corner, top edge half
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.875, position.y)
    ac.glVertex2f(position.x + size.width * 0.9228, position.y + size.width * 0.0095)
    ac.glVertex2f(position.x + size.width * 0.9634, position.y + size.width * 0.0366)
    # top right corner, right edge half
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.9634, position.y + size.width * 0.0366)
    ac.glVertex2f(position.x + size.width * 0.9905, position.y + size.width * 0.0772)
    ac.glVertex2f(position.x + size.width, position.y + size.width * 0.125)
    ac.glEnd()

    ac.glBegin(acsys.GL.Quads)
    # bottom right corner, right edge half
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.9905, position.y + size.height - size.width * 0.0772)
    ac.glVertex2f(position.x + size.width * 0.9634, position.y + size.height - size.width * 0.0366)
    # bottom right corner, bottom edge half
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.9634, position.y + size.height - size.width * 0.0366)
    ac.glVertex2f(position.x + size.width * 0.9228, position.y + size.height - size.width * 0.0095)
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.height)
    ac.glEnd()

    ac.glBegin(acsys.GL.Quads)
    # bottom left corner, bottom edge half
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.height)
    ac.glVertex2f(position.x + size.width * 0.0772, position.y + size.height - size.width * 0.0095)
    ac.glVertex2f(position.x + size.width * 0.0366, position.y + size.height - size.width * 0.0366)
    # bottom left corner, left edge half
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.0366, position.y + size.height - size.width * 0.0366)
    ac.glVertex2f(position.x + size.width * 0.0095, position.y + size.height - size.width * 0.0772)
    ac.glVertex2f(position.x, position.y + size.height - size.width * 0.125)
    ac.glEnd()


def draw_tire(position: Position, ratio: float, settings: Settings) -> None:
    size = Size(64 * settings.scale, 104 * settings.scale)
    if ratio < 0:
        color = Color.grey.mix(Color.purple, level(settings.lock, ratio))
    else:
        color = Color.grey.mix(Color.amber, level(settings.spin, ratio))
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    # middle column, full height
    ac.glQuad(position.x + size.width * 0.125, position.y, size.width * 0.75, size.height)
    # left column, between the corners
    ac.glQuad(position.x, position.y + size.width * 0.125, size.width * 0.125, size.height - size.width * 0.25)
    # right column, between the corners
    ac.glQuad(position.x + size.width * 0.875, position.y + size.width * 0.125, size.width * 0.125, size.height - size.width * 0.25)  # fmt: skip

    ac.glBegin(acsys.GL.Quads)
    # top left corner, left edge half
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.width * 0.125)
    ac.glVertex2f(position.x, position.y + size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.0095, position.y + size.width * 0.0772)
    ac.glVertex2f(position.x + size.width * 0.0366, position.y + size.width * 0.0366)
    # top left corner, top edge half
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.0366, position.y + size.width * 0.0366)
    ac.glVertex2f(position.x + size.width * 0.0772, position.y + size.width * 0.0095)
    ac.glVertex2f(position.x + size.width * 0.125, position.y)
    ac.glEnd()

    ac.glBegin(acsys.GL.Quads)
    # top right corner, top edge half
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.875, position.y)
    ac.glVertex2f(position.x + size.width * 0.9228, position.y + size.width * 0.0095)
    ac.glVertex2f(position.x + size.width * 0.9634, position.y + size.width * 0.0366)
    # top right corner, right edge half
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.9634, position.y + size.width * 0.0366)
    ac.glVertex2f(position.x + size.width * 0.9905, position.y + size.width * 0.0772)
    ac.glVertex2f(position.x + size.width, position.y + size.width * 0.125)
    ac.glEnd()

    ac.glBegin(acsys.GL.Quads)
    # bottom right corner, right edge half
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.9905, position.y + size.height - size.width * 0.0772)
    ac.glVertex2f(position.x + size.width * 0.9634, position.y + size.height - size.width * 0.0366)
    # bottom right corner, bottom edge half
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.9634, position.y + size.height - size.width * 0.0366)
    ac.glVertex2f(position.x + size.width * 0.9228, position.y + size.height - size.width * 0.0095)
    ac.glVertex2f(position.x + size.width * 0.875, position.y + size.height)
    ac.glEnd()

    ac.glBegin(acsys.GL.Quads)
    # bottom left corner, bottom edge half
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.height)
    ac.glVertex2f(position.x + size.width * 0.0772, position.y + size.height - size.width * 0.0095)
    ac.glVertex2f(position.x + size.width * 0.0366, position.y + size.height - size.width * 0.0366)
    # bottom left corner, left edge half
    ac.glVertex2f(position.x + size.width * 0.125, position.y + size.height - size.width * 0.125)
    ac.glVertex2f(position.x + size.width * 0.0366, position.y + size.height - size.width * 0.0366)
    ac.glVertex2f(position.x + size.width * 0.0095, position.y + size.height - size.width * 0.0772)
    ac.glVertex2f(position.x, position.y + size.height - size.width * 0.125)
    ac.glEnd()


def draw_arrow(position: Position, slip: float, settings: Settings) -> None:
    size = Size(38.4 * settings.scale, 280 * settings.scale)
    third = size.width / 3
    neck = position.y + third * 2

    color = Color.grey.mix(Color.red, level(settings.body_slip, slip))
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x + third, neck, third, position.y + size.height - neck)

    ac.glBegin(acsys.GL.Triangles)
    ac.glVertex2f(position.x, neck)
    ac.glVertex2f(position.x + size.width, neck)
    ac.glVertex2f(position.x + size.width / 2, position.y)
    ac.glEnd()


class WidgetApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        self.id = ac.newApp("Butt Meter")
        ac.setTitle(self.id, "")
        ac.setIconPosition(self.id, 0, -10000)
        ac.drawBorder(self.id, 0)

        self.listeners = []

        self.scale_buttons(self.on_scale_change)
        self.update_scale_buttons(self.settings.scale)

        # AC does not hold a reference to callbacks, so keep the bound method alive
        self.callback = self.render
        ac.addRenderCallback(self.id, self.callback)

    def scale_buttons(self, on_change: object) -> None:
        def on_grow(x: float, y: float) -> None:
            index = SCALES.index(self.settings.scale)
            if index < len(SCALES) - 1:
                on_change(SCALES[index + 1])

        def on_shrink(x: float, y: float) -> None:
            index = SCALES.index(self.settings.scale)
            if index > 0:
                on_change(SCALES[index - 1])

        self.grow_button = scale_button(self.id, on_grow)
        self.shrink_button = scale_button(self.id, on_shrink)

        self.listeners.extend((on_grow, on_shrink))

    def on_scale_change(self, scale: float) -> None:
        self.settings.scale = scale
        save_settings(self.settings)

    def update_scale_buttons(self, scale: float):
        ac.setSize(self.id, 248 * scale, 24 + 336 * scale)
        ac.setPosition(self.grow_button, 248 * scale - 80, 3)
        ac.setPosition(self.shrink_button, 248 * scale - 54, 3)

    def render(self, _: float) -> None:
        ac.setBackgroundOpacity(self.id, 0.025)
        snapshot = read_snapshot()

        fl, fr, rl, rr = snapshot.wheels
        settings = self.settings
        scale = settings.scale

        can_grow = scale == SCALES[-1]
        grow_color = Color.white.brightness(0.2) if can_grow else Color.white
        draw_grow_icon(Position(248 * scale - 80, 3), grow_color)

        can_shrink = scale == SCALES[0]
        shrink_color = Color.white.brightness(0.2) if can_shrink else Color.white
        draw_shrink_icon(Position(248 * scale - 54, 3), shrink_color)

        draw_line(Position(0, 24), scale, fl.slip_angle, settings.understeer, Color.teal)
        draw_line(Position(184 * scale, 24), scale, fr.slip_angle, settings.understeer, Color.teal)

        draw_tire(Position(0, 24 + 28 * scale), fl.slip_ratio, settings)
        draw_arrow(Position(104.8 * scale, 24 + 28 * scale), snapshot.body_slip, settings)
        draw_tire(Position(184 * scale, 24 + 28 * scale), fr.slip_ratio, settings)

        draw_tire(Position(0, 24 + 204 * scale), rl.slip_ratio, settings)
        draw_tire(Position(184 * scale, 24 + 204 * scale), rr.slip_ratio, settings)

        draw_line(Position(0, 24 + 316 * scale), scale, rl.slip_angle, settings.oversteer, Color.red)
        draw_line(Position(184 * scale, 24 + 316 * scale), scale, rr.slip_angle, settings.oversteer, Color.red)

import ac, acsys

from render import Color, Position, Size
from settings import Settings, Threshold, save_settings, slip_fill
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


def draw_rounded_corner(center: Position, radius: float, horizontal: float, vertical: float, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glBegin(acsys.GL.Quads)
    ac.glVertex2f(center.x, center.y)
    ac.glVertex2f(center.x + horizontal * radius, center.y)
    ac.glVertex2f(center.x + horizontal * radius * 0.9239, center.y + vertical * radius * 0.3827)
    ac.glVertex2f(center.x + horizontal * radius * 0.7071, center.y + vertical * radius * 0.7071)
    ac.glVertex2f(center.x, center.y)
    ac.glVertex2f(center.x + horizontal * radius * 0.7071, center.y + vertical * radius * 0.7071)
    ac.glVertex2f(center.x + horizontal * radius * 0.3827, center.y + vertical * radius * 0.9239)
    ac.glVertex2f(center.x, center.y + vertical * radius)
    ac.glEnd()


def draw_rounded_block(position: Position, size: Size, radius: float, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x + radius, position.y, size.width - radius * 2, size.height)
    ac.glQuad(position.x, position.y + radius, radius, size.height - radius * 2)
    ac.glQuad(position.x + size.width - radius, position.y + radius, radius, size.height - radius * 2)

    left = position.x + radius
    right = position.x + size.width - radius
    top = position.y + radius
    bottom = position.y + size.height - radius

    draw_rounded_corner(Position(left, top), radius, -1, -1, color)
    draw_rounded_corner(Position(right, top), radius, 1, -1, color)
    draw_rounded_corner(Position(right, bottom), radius, 1, 1, color)
    draw_rounded_corner(Position(left, bottom), radius, -1, 1, color)


def draw_line(position: Position, scale: float, angle: float, threshold: Threshold, slide_color: Color) -> None:
    size = Size(64 * scale, 20 * scale)
    color = Color.grey.mix(slide_color, threshold.level(angle))
    draw_rounded_block(position, size, size.width * 0.125, color)


def draw_tire_column(position: Position, size: Size, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuad(position.x, position.y, size.width, size.height)


def draw_tire_corner(center: Position, radius: float, horizontal: float, vertical: float, color: Color) -> None:
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glBegin(acsys.GL.Quads)
    ac.glVertex2f(center.x, center.y)
    ac.glVertex2f(center.x + horizontal * radius, center.y)
    ac.glVertex2f(center.x + horizontal * radius * 0.9239, center.y + vertical * radius * 0.3827)
    ac.glVertex2f(center.x + horizontal * radius * 0.7071, center.y + vertical * radius * 0.7071)
    ac.glVertex2f(center.x, center.y)
    ac.glVertex2f(center.x + horizontal * radius * 0.7071, center.y + vertical * radius * 0.7071)
    ac.glVertex2f(center.x + horizontal * radius * 0.3827, center.y + vertical * radius * 0.9239)
    ac.glVertex2f(center.x, center.y + vertical * radius)
    ac.glEnd()


def draw_tire(position: Position, scale: float, fill: Color) -> None:
    size = Size(64 * scale, 104 * scale)
    radius = size.width * 0.125

    left = position.x + radius
    right = position.x + size.width - radius
    top = position.y + radius
    bottom = position.y + size.height - radius

    middle = Size(size.width - radius * 2, size.height)
    side = Size(radius, size.height - radius * 2)

    draw_tire_column(Position(left, position.y), middle, fill)
    draw_tire_column(Position(position.x, top), side, fill)
    draw_tire_column(Position(right, top), side, fill)

    draw_tire_corner(Position(left, top), radius, -1, -1, fill)
    draw_tire_corner(Position(right, top), radius, 1, -1, fill)
    draw_tire_corner(Position(right, bottom), radius, 1, 1, fill)
    draw_tire_corner(Position(left, bottom), radius, -1, 1, fill)


def draw_arrow(position: Position, slip: float, settings: Settings) -> None:
    size = Size(38.4 * settings.scale, 280 * settings.scale)
    third = size.width / 3
    neck = position.y + third * 2

    color = Color.grey.mix(Color.red, settings.body_slip.level(slip))
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

        draw_tire(Position(0, 24 + 28 * scale), scale, slip_fill(fl.slip_ratio, settings.lock, settings.spin, Color.purple, Color.amber))  # fmt: skip
        draw_arrow(Position(104.8 * scale, 24 + 28 * scale), snapshot.body_slip, settings)
        draw_tire(Position(184 * scale, 24 + 28 * scale), scale, slip_fill(fr.slip_ratio, settings.lock, settings.spin, Color.purple, Color.amber))  # fmt: skip

        draw_tire(Position(0, 24 + 204 * scale), scale, slip_fill(rl.slip_ratio, settings.lock, settings.spin, Color.purple, Color.amber))  # fmt: skip
        draw_tire(Position(184 * scale, 24 + 204 * scale), scale, slip_fill(rr.slip_ratio, settings.lock, settings.spin, Color.purple, Color.amber))  # fmt: skip

        draw_line(Position(0, 24 + 316 * scale), scale, rl.slip_angle, settings.oversteer, Color.red)
        draw_line(Position(184 * scale, 24 + 316 * scale), scale, rr.slip_angle, settings.oversteer, Color.red)

import ac, os

from render import Color, Position, Size
from config import Settings, save_settings, slip_ratio_fill, threshold_fill
from telemetry import read_snapshot

SCALES = (0.5, 2 / 3, 1.0)


def scale_button(app_id: int, on_click: object) -> int:
    button = ac.addButton(app_id, "")
    ac.drawBorder(button, 0)
    ac.setBackgroundOpacity(button, 0)
    ac.setSize(button, 18, 18)
    ac.addOnClickedListener(button, on_click)
    return button


def draw_icon(position: Position, color: Color, texture: int) -> None:
    size = Size(18, 18)
    ac.glColor4f(color.red, color.green, color.blue, color.alpha)
    ac.glQuadTextured(position.x, position.y, size.width, size.height, texture)


def load_texture(name: str) -> int:
    folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures")
    return ac.newTexture(os.path.join(folder, name + ".png"))


def draw_line(position: Position, scale: float, fill: Color, texture: int) -> None:
    size = Size(64 * scale, 20 * scale)
    ac.glColor4f(fill.red, fill.green, fill.blue, fill.alpha)
    ac.glQuadTextured(position.x, position.y, size.width, size.height, texture)


def draw_tire(position: Position, scale: float, fill: Color, texture: int) -> None:
    size = Size(64 * scale, 104 * scale)
    ac.glColor4f(fill.red, fill.green, fill.blue, fill.alpha)
    ac.glQuadTextured(position.x, position.y, size.width, size.height, texture)


def draw_arrow(position: Position, scale: float, fill: Color, texture: int) -> None:
    size = Size(38.4 * scale, 280 * scale)
    ac.glColor4f(fill.red, fill.green, fill.blue, fill.alpha)
    ac.glQuadTextured(position.x, position.y, size.width, size.height, texture)


class WidgetApplication:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def initialize(self) -> None:
        self.id = ac.newApp("Butt Meter")
        ac.setTitle(self.id, "")
        ac.setIconPosition(self.id, 0, -10000)
        ac.drawBorder(self.id, 0)

        self.listeners = []

        self.tire_texture = load_texture("tire")
        self.line_texture = load_texture("line")
        self.arrow_texture = load_texture("arrow")
        self.grow_texture = load_texture("grow")
        self.shrink_texture = load_texture("shrink")

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
        self.update_scale_buttons(scale)

    def update_scale_buttons(self, scale: float):
        ac.setSize(self.id, 248 * scale, 30 + 336 * scale)
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
        draw_icon(Position(248 * scale - 80, 3), grow_color, self.grow_texture)

        can_shrink = scale == SCALES[0]
        shrink_color = Color.white.brightness(0.2) if can_shrink else Color.white
        draw_icon(Position(248 * scale - 54, 3), shrink_color, self.shrink_texture)

        draw_line(Position(0, 30), scale, threshold_fill(fl.slip_angle, settings.understeer, Color.teal), self.line_texture)  # fmt: skip
        draw_line(Position(184 * scale, 30), scale, threshold_fill(fr.slip_angle, settings.understeer, Color.teal), self.line_texture)  # fmt: skip

        draw_tire(Position(0, 30 + 28 * scale), scale, slip_ratio_fill(fl.slip_ratio, settings.lock, settings.spin), self.tire_texture)  # fmt: skip
        draw_arrow(Position(104.8 * scale, 30 + 28 * scale), scale, threshold_fill(snapshot.body_slip, settings.body_slip, Color.red), self.arrow_texture)  # fmt: skip
        draw_tire(Position(184 * scale, 30 + 28 * scale), scale, slip_ratio_fill(fr.slip_ratio, settings.lock, settings.spin), self.tire_texture)  # fmt: skip

        draw_tire(Position(0, 30 + 204 * scale), scale, slip_ratio_fill(rl.slip_ratio, settings.lock, settings.spin), self.tire_texture)  # fmt: skip
        draw_tire(Position(184 * scale, 30 + 204 * scale), scale, slip_ratio_fill(rr.slip_ratio, settings.lock, settings.spin), self.tire_texture)  # fmt: skip

        draw_line(Position(0, 30 + 316 * scale), scale, threshold_fill(rl.slip_angle, settings.oversteer, Color.red), self.line_texture)  # fmt: skip
        draw_line(Position(184 * scale, 30 + 316 * scale), scale, threshold_fill(rr.slip_angle, settings.oversteer, Color.red), self.line_texture)  # fmt: skip

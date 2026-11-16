# Wheel-slip widget for Assetto Corsa: four tyres, colour = each tyre's slip ratio as AC's
# physics reports it (acsys.CS.SlipRatio). Negative = locking, positive = spinning.
# Dotted line = the car's own axis, nose to tail. Solid line with the arrow head = the
# direction of travel through the car centre (body slip angle). Lines together = car goes
# where it points; solid line tilted = car is rotating/sliding, head points the way to
# countersteer. Colour works like the tyres: grey up to start, grey->red to full.
# White lines above the front tyres and below the rear ones = each tyre's slip angle
# (acsys.CS.SlipAngle), tyre-wide. Hidden up to angle start, grey->white to full, held like
# the tyres.
# A second window ("WheelLock Settings") shows the live signals, the colour curves and the
# thresholds, and lets you edit them. Open it with the sliders button on the widget.
#
# Runs in AC's embedded Python 3.3: no f-strings, no typing module, no variable annotations,
# no dataclasses: records are plain classes with __slots__, replaced, not mutated.
# Helpers are stateless: everything they need comes in as parameters. Mutable state lives
# only in the four globals under "app state", changed only by the AC callbacks at the bottom.
import json
import math
import os
import time
import ac
import acsys


# --- records ------------------------------------------------------------------
class Record:
    __slots__ = ()

    def replace(self, **changes: object) -> "Record":
        values = fields(self)
        values.update(changes)
        return type(self)(**values)


def fields(record: Record) -> dict:
    return {name: getattr(record, name) for name in record.__slots__}


class Settings(Record):
    __slots__ = ("scale", "lock", "spin", "rotate", "angle", "min_speed", "hold_ms")

    def __init__(self, scale: float, lock: tuple, spin: tuple, rotate: tuple, angle: tuple,
                 min_speed: float, hold_ms: float) -> None:
        self.scale = scale
        self.lock = lock
        self.spin = spin
        self.rotate = rotate
        self.angle = angle
        self.min_speed = min_speed
        self.hold_ms = hold_ms


class Hold(Record):
    __slots__ = ("remaining", "color")

    def __init__(self, remaining: float, color: tuple) -> None:
        self.remaining = remaining
        self.color = color


class State(Record):
    __slots__ = ("speed", "slips", "angles", "angles_shown", "angle_holds", "shown", "holds",
                 "velocity", "beta", "beta_shown", "beta_hold")

    def __init__(self, speed: float, slips: tuple, angles: tuple, angles_shown: tuple,
                 angle_holds: tuple, shown: tuple, holds: tuple, velocity: tuple, beta: float,
                 beta_shown: tuple, beta_hold: Hold) -> None:
        self.speed = speed
        self.slips = slips
        self.angles = angles
        self.angles_shown = angles_shown
        self.angle_holds = angle_holds
        self.shown = shown
        self.holds = holds
        self.velocity = velocity
        self.beta = beta
        self.beta_shown = beta_shown
        self.beta_hold = beta_hold


class Layout(Record):
    __slots__ = ("width", "height", "tyres", "buttons", "center", "reach")

    def __init__(self, width: int, height: int, tyres: list, buttons: list, center: tuple,
                 reach: float) -> None:
        self.width = width
        self.height = height
        self.tyres = tyres
        self.buttons = buttons
        self.center = center
        self.reach = reach


class Label(Record):
    __slots__ = ("key", "text", "left", "top", "size")

    def __init__(self, key: str, text: object, left: float, top: float, size: int = 13) -> None:
        self.key = key
        self.text = text
        self.left = left
        self.top = top
        self.size = size


class Spinner(Record):
    __slots__ = ("key", "left", "top", "low", "high", "step")

    def __init__(self, key: str, left: float, top: float, low: int, high: int,
                 step: int = 1) -> None:
        self.key = key
        self.left = left
        self.top = top
        self.low = low
        self.high = high
        self.step = step


class Ui(Record):
    __slots__ = ("app", "buttons", "settings_window", "controls", "listeners",
                 "settings_open", "quiet")

    def __init__(self, app: int, buttons: list, settings_window: int, controls: dict,
                 listeners: list, settings_open: bool, quiet: bool) -> None:
        self.app = app
        self.buttons = buttons
        self.settings_window = settings_window
        self.controls = controls
        self.listeners = listeners
        self.settings_open = settings_open
        self.quiet = quiet


SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
# AC resets window opacity while it's dragged/hovered; a transparent texture keeps it invisible then.
BACKGROUND = "apps/python/WheelLock/img/bg.png"

# --- settings (edited in the settings window, saved to settings.json) ---------
# lock/spin: [start, full] in % of |SlipRatio|, start < full.
# rotate: [start, full] in degrees of body slip angle. Defaults from recorded laps
# (mp4-12c GT3, Laguna Seca): grip stays under 3 deg 90% of the time; once a slide passes
# 8 deg 28% of them ended in a spin, and the spins only got countersteer at 10-14 deg.
# angle: [start, full] in degrees of tyre SlipAngle.
DEFAULTS = Settings(scale=1.0, lock=(2, 10), spin=(2, 10), rotate=(3, 8), angle=(6, 10),
                    min_speed=10, hold_ms=120)

# --- colours (rgba) -----------------------------------------------------------
GREY = (0.25, 0.25, 0.25, 0.8)  # |slip| <= start, or car slower than min speed
PURPLE = (0.6, 0.3, 1.0, 1.0)   # lock at full
AMBER = (1.0, 0.69, 0.0, 1.0)   # spin at full
RED = (1.0, 0.2, 0.2, 1.0)      # rotation at full
WHITE = (1.0, 1.0, 1.0, 1.0)
FAINT = (1.0, 1.0, 1.0, 0.15)   # empty track behind a live marker
AXIS = (1.0, 1.0, 1.0, 0.3)     # dotted car axis on the widget
SLIP_LINE = (0.9, 0.9, 0.9, 0.85)  # tyre slip angle line at full
HIDDEN = (0.0, 0.0, 0.0, 0.0)      # slip angle line below start
BUTTON_ON = (1.0, 1.0, 1.0, 0.7)
BUTTON_OFF = (1.0, 1.0, 1.0, 0.2)  # at min/max scale

# --- widget layout (px at scale 1.0) ------------------------------------------
TYRE_WIDTH, TYRE_HEIGHT = 16, 26
TRACK_GAP, AXLE_GAP = 30, 18   # left-right gap, front-rear gap
LINE_GAP = 6                   # strip above front / below rear tyres for the slip angle lines
SCALES = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
TOP_STRIP = 24   # kept free of tyres: AC/CSP draw the pin there, our buttons sit beside it
PIN_WIDTH = 28   # right end of TOP_STRIP reserved for CSP's pin button
BUTTON = 16      # button size

# --- settings window layout (px) ----------------------------------------------
SETTINGS_SIZE = (430, 830)
PLOT_X, PLOT_WIDTH = 110, 270    # x axis of both curves and the live rows
CURVE_HEIGHT = 20
SLIP_Y = 110                     # slip curve
ROW_Y, ROW_HEIGHT = 140, 20      # FL, FR, RL, RR rows below the slip curve
SWATCH_X = PLOT_X + PLOT_WIDTH + 12  # colour the widget is showing right now
ANGLE_Y = 270                    # slip angle curve
ANGLE_ROW_Y = ANGLE_Y + 30       # FL, FR, RL, RR slip angle rows under it
BETA_Y = 420                     # rotation curve
BETA_ROW_Y = BETA_Y + 30         # live beta row under its curve
RULES_Y, THRESHOLDS_Y = 485, 630
SPINNER_SIZE = (90, 20)
WHEELS = ("FL", "FR", "RL", "RR")

# Exactly what acUpdate does, shown in the settings window.
RULES = (
    "every frame, focused car:",
    "  SpeedKMH < min speed            -> all tyres grey, arrow grey and straight up",
    "  SlipRatio < 0 (lock):  |s| <= start grey, start..full grey->purple, >= full purple",
    "  SlipRatio > 0 (spin):  |s| <= start grey, start..full grey->amber,  >= full amber",
    "  SlipAngle (angle):     |a| <= start no line, start..full grey->white, >= full white",
    "  beta = atan2(-x, z) of LocalVelocity, + = travelling right of the nose, arrow tilts",
    "  beta (rotate):         |b| <= start grey, start..full grey->red,    >= full red",
    "  |value| >= full and speed >= min -> that colour stays for hold ms",
)

IDLE = State(speed=0.0, slips=(0.0,) * 4, angles=(0.0,) * 4, angles_shown=(HIDDEN,) * 4,
             angle_holds=(Hold(0.0, HIDDEN),) * 4, shown=(GREY,) * 4,
             holds=(Hold(0.0, GREY),) * 4, velocity=(0.0, 0.0, 0.0), beta=0.0, beta_shown=GREY, beta_hold=Hold(0.0, GREY))


# --- math ---------------------------------------------------------------------
def remap(value: float, from_min: float, from_max: float, to_min: float, to_max: float) -> float:
    """value in from_min..from_max -> same position in to_min..to_max, clamped to the ends."""
    clamped = max(from_min, min(from_max, value))
    fraction = (clamped - from_min) / (from_max - from_min)
    return to_min + fraction * (to_max - to_min)


def blend(color_from: tuple, color_to: tuple, fraction: float) -> tuple:
    return tuple(start + (end - start) * fraction for start, end in zip(color_from, color_to))


def ramp(magnitude: float, start: float, full: float, hot: tuple) -> tuple:
    """Grey up to start, grey->hot from start to full, hot beyond."""
    return blend(GREY, hot, remap(magnitude, start, full, 0.0, 1.0))


def shift(point: tuple, direction: tuple, distance: float) -> tuple:
    return (point[0] + direction[0] * distance, point[1] + direction[1] * distance)


# --- model --------------------------------------------------------------------
def slip_limits(slip: float, settings: Settings) -> tuple:
    return settings.lock if slip < 0 else settings.spin


def slip_color(slip: float, settings: Settings) -> tuple:
    """SlipRatio -> colour through the lock/spin thresholds (% of |SlipRatio|)."""
    start, full = slip_limits(slip, settings)
    return ramp(abs(slip) * 100, start, full, PURPLE if slip < 0 else AMBER)


def slip_full(slip: float, settings: Settings) -> bool:
    return abs(slip) * 100 >= slip_limits(slip, settings)[1]


def beta_color(beta: float, settings: Settings) -> tuple:
    """Body slip angle (deg) -> colour through the rotate thresholds, same ramp as the tyres."""
    start, full = settings.rotate
    return ramp(abs(beta), start, full, RED)


def angle_color(angle: float, settings: Settings) -> tuple:
    """Tyre SlipAngle (deg) -> hidden up to start, then the same ramp as the tyres to white."""
    start, full = settings.angle
    if abs(angle) <= start:
        return HIDDEN
    return ramp(abs(angle), start, full, SLIP_LINE)


def body_slip(velocity: tuple, speed: float, min_speed: float) -> float:
    """Angle (deg) between where the car points and where it travels; + = travel to the right.
    AC's local frame is y up, z forward, x left, so right = -x (checked against tyre contact
    points in recordings; in slides drivers countersteer to the side this points)."""
    if speed < min_speed:
        return 0.0  # direction of a near-zero velocity is noise
    return math.degrees(math.atan2(-velocity[0], velocity[2]))


def hold(color: tuple, at_full: bool, previous: Hold, delta: float, duration: float) -> tuple:
    """-> (colour to show, new Hold): a full colour stays on screen for duration seconds,
    so a short lock or snap is still seen."""
    if at_full:
        return color, Hold(duration, color)
    remaining = previous.remaining - delta
    if remaining > 0:
        return previous.color, Hold(remaining, previous.color)
    return color, Hold(0.0, previous.color)


def tyre_step(slip: float, speed: float, previous: Hold, delta: float,
              settings: Settings) -> tuple:
    """-> (colour to show, new Hold) for one tyre this frame."""
    moving = speed >= settings.min_speed
    color = slip_color(slip, settings) if moving else GREY
    at_full = moving and slip_full(slip, settings)
    return hold(color, at_full, previous, delta, settings.hold_ms / 1000.0)


def angle_step(angle: float, speed: float, previous: Hold, delta: float,
               settings: Settings) -> tuple:
    """-> (colour to show, new Hold) for one tyre's slip angle line this frame."""
    moving = speed >= settings.min_speed
    color = angle_color(angle, settings) if moving else HIDDEN
    at_full = moving and abs(angle) >= settings.angle[1]
    return hold(color, at_full, previous, delta, settings.hold_ms / 1000.0)


def advance(state: State, speed: float, slips: list, angles: list, velocity: tuple,
            delta: float, settings: Settings) -> State:
    """Next frame's state from this frame's telemetry. No look-ahead on the beta rate: in
    recordings spins (11-62 deg/s) and saves (4-87 deg/s) overlap, so prediction only added
    false reds."""
    tyres = [tyre_step(slip, speed, previous, delta, settings)
             for slip, previous in zip(slips, state.holds)]
    lines = [angle_step(angle, speed, previous, delta, settings)
             for angle, previous in zip(angles, state.angle_holds)]
    beta =body_slip(velocity, speed, settings.min_speed)
    beta_full = abs(beta) >= settings.rotate[1]
    beta_shown, beta_hold = hold(beta_color(beta, settings), beta_full, state.beta_hold,
                                 delta, settings.hold_ms / 1000.0)
    return State(speed=speed, slips=tuple(slips), angles=tuple(angles),
                 angles_shown=tuple(color for color, _ in lines),
                 angle_holds=tuple(line_hold for _, line_hold in lines),
                 shown=tuple(color for color, _ in tyres),
                 holds=tuple(tyre_hold for _, tyre_hold in tyres),
                 velocity=tuple(velocity), beta=beta,
                 beta_shown=beta_shown, beta_hold=beta_hold)


# --- settings file ------------------------------------------------------------
def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_valid(key: str, value: object) -> bool:
    """Is value an acceptable saved value for setting key?"""
    if key == "scale":
        return value in SCALES
    if key in ("lock", "spin", "rotate", "angle"):
        return (isinstance(value, list) and len(value) == 2 and all(map(is_number, value))
                and 0 <= value[0] < value[1] <= 100)
    if key == "min_speed":
        return is_number(value) and 0 <= value <= 100
    if key == "hold_ms":
        return is_number(value) and 0 <= value <= 1000
    return False


def load_settings(path: str) -> tuple:
    """-> (Settings, status): defaults, overlaid key by key with every valid saved value."""
    try:
        with open(path) as file:
            saved = json.load(file)
    except IOError:
        return DEFAULTS, "no file yet, defaults"
    except ValueError as error:
        return DEFAULTS, "unreadable, defaults: {}".format(error)
    if not isinstance(saved, dict):
        saved = {}
    keys = Settings.__slots__
    rejected = sorted(key for key in keys if key in saved and not is_valid(key, saved[key]))
    accepted = {key: tuple(saved[key]) if isinstance(saved[key], list) else saved[key]
                for key in keys if key in saved and key not in rejected}
    status = "loaded" + (", reset to default: " + ", ".join(rejected) if rejected else "")
    return DEFAULTS.replace(**accepted), status


def save_settings(settings: Settings, path: str) -> str:
    """-> status. Writes a temp file then os.replace: a crash mid-write can't leave a half
    file that the next load would throw away."""
    temp = path + ".tmp"
    try:
        with open(temp, "w") as file:
            json.dump(fields(settings), file, indent=1, sort_keys=True)
        os.replace(temp, path)
        return "saved " + time.strftime("%H:%M:%S")
    except (IOError, OSError) as error:
        return "NOT SAVED: {}".format(error)


def with_threshold(settings: Settings, kind: str, index: int, value: float) -> Settings:
    """Copy of settings with threshold kind[index] (0 start, 1 full) set to value, the other
    one pushed so start < full."""
    pair = list(getattr(settings, kind))
    pair[index] = max(index, min(99 + index, int(value)))
    if index == 0:
        pair[1] = max(pair[1], pair[0] + 1)
    else:
        pair[0] = min(pair[0], pair[1] - 1)
    return settings.replace(**{kind: tuple(pair)})


def spinner_value(settings: Settings, key: str) -> float:
    """Spinner key 'lock.0' -> lock start; 'min_speed' -> plain value."""
    if "." in key:
        kind, index = key.split(".")
        return getattr(settings, kind)[int(index)]
    return getattr(settings, key)


def with_spinner(settings: Settings, key: str, value: float) -> Settings:
    if "." in key:
        kind, index = key.split(".")
        return with_threshold(settings, kind, int(index), value)
    return settings.replace(**{key: int(value)})


def with_scale(settings: Settings, step: int) -> Settings:
    index = max(0, min(len(SCALES) - 1, SCALES.index(settings.scale) + step))
    return settings.replace(scale=SCALES[index])


# --- widget window ------------------------------------------------------------
def geometry(scale: float) -> Layout:
    """Window size, tyre rects (FL, FR, RL, RR), button positions (settings, shrink, grow)
    and the car centre and half-length at this scale."""
    tyre_width, tyre_height = int(TYRE_WIDTH * scale), int(TYRE_HEIGHT * scale)
    track, axle = int(TRACK_GAP * scale), int(AXLE_GAP * scale)
    line_gap = int(LINE_GAP * scale)
    car_width = tyre_width * 2 + track
    car_top = TOP_STRIP + line_gap
    reach = tyre_height + axle / 2.0  # car centre to the front edge of the tyres
    width = max(car_width, int(2 * reach + 4 * scale), PIN_WIDTH + 3 * (BUTTON + 4) + 4)
    car_left = (width - car_width) // 2
    tyres = [(tyre_x, tyre_y, tyre_width, tyre_height)
             for tyre_y in (car_top, car_top + tyre_height + axle)
             for tyre_x in (car_left, car_left + tyre_width + track)]
    buttons_left = width - PIN_WIDTH - 3 * (BUTTON + 4)
    buttons_top = (TOP_STRIP - BUTTON) // 2
    return Layout(width=width, height=car_top + tyre_height * 2 + axle + line_gap, tyres=tyres,
                  buttons=[(buttons_left + index * (BUTTON + 4), buttons_top)
                           for index in range(3)],
                  center=(width / 2.0, car_top + reach), reach=reach)


def draw_polygon(mode: int, points: list) -> None:
    ac.glBegin(mode)
    for point in points:
        ac.glVertex2f(*point)
    ac.glEnd()


def draw_arrow(tail: tuple, head: tuple, thickness: float) -> None:
    """Filled arrow from tail to head: quad shaft, triangle head."""
    length = math.hypot(head[0] - tail[0], head[1] - tail[1])
    along = ((head[0] - tail[0]) / length, (head[1] - tail[1]) / length)
    across = (-along[1], along[0])
    base = shift(head, along, -thickness * 2.2)  # where the head starts
    shaft, head_half = thickness / 2, thickness * 1.6
    draw_polygon(acsys.GL.Quads, [shift(tail, across, shaft), shift(base, across, shaft),
                                  shift(base, across, -shaft), shift(tail, across, -shaft)])
    draw_polygon(acsys.GL.Triangles, [head, shift(base, across, head_half),
                                      shift(base, across, -head_half)])


def draw_resize_icon(left: float, top: float, outward: bool) -> None:
    """Two diagonal arrows: pointing to the corners (grow) or to the centre (shrink)."""
    margin, gap, middle = BUTTON * 0.12, BUTTON * 0.1, BUTTON / 2.0
    for side in (-1, 1):
        corner = (left + middle + side * (middle - margin), top + middle + side * (middle - margin))
        inner = (left + middle + side * gap, top + middle + side * gap)
        tail, head = (inner, corner) if outward else (corner, inner)
        draw_arrow(tail, head, 1.6)


def draw_sliders_icon(left: float, top: float) -> None:
    """Three lines with knobs: settings."""
    for index, knob in enumerate((0.3, 0.7, 0.45)):
        line_y = top + BUTTON * (0.25 + 0.25 * index)
        ac.glQuad(left + 1, line_y - 0.75, BUTTON - 2, 1.5)
        ac.glQuad(left + BUTTON * knob - 2, line_y - 2.5, 4, 5)


def draw_car_axis(center: tuple, reach: float, scale: float) -> None:
    """Dotted line nose to tail: thin and faint, drawn under the travel arrow."""
    center_x, center_y = center
    dash, thickness = 3 * scale, max(1.0, 0.75 * scale)
    ac.glColor4f(*AXIS)
    dash_top = center_y - reach
    while dash_top < center_y + reach:
        ac.glQuad(center_x - thickness / 2, dash_top, thickness,
                  min(dash, center_y + reach - dash_top))
        dash_top += dash * 2  # gap = dash


def draw_travel(center: tuple, reach: float, beta: float, color: tuple, scale: float) -> None:
    """Solid arrow through the car centre, rotated by beta, head at the front end."""
    angle = math.radians(max(-90.0, min(90.0, beta)))  # past 90 deg it's a spin; red says enough
    offset_x, offset_y = reach * math.sin(angle), reach * math.cos(angle)
    center_x, center_y = center
    ac.glColor4f(*color)
    draw_arrow((center_x - offset_x, center_y + offset_y),
               (center_x + offset_x, center_y - offset_y), 3 * scale)


def draw_slip_angles(tyres: list, colors: tuple, scale: float) -> None:
    """Tyre-wide line above each front tyre and below each rear one, in its slip angle colour."""
    thickness, gap = max(1.0, 2 * scale), LINE_GAP * scale
    for index, ((left, top, width, height), color) in enumerate(zip(tyres, colors)):
        line_y = top - gap / 2 if index < 2 else top + height + gap / 2
        ac.glColor4f(*color)
        ac.glQuad(left, line_y - thickness / 2, width, thickness)


def draw_buttons(positions: list, scale: float) -> None:
    index = SCALES.index(scale)
    ac.glColor4f(*BUTTON_ON)
    draw_sliders_icon(*positions[0])
    for position, outward, enabled in zip(positions[1:], (False, True),
                                          (index > 0, index < len(SCALES) - 1)):
        ac.glColor4f(*(BUTTON_ON if enabled else BUTTON_OFF))
        draw_resize_icon(position[0], position[1], outward)


def draw_widget(layout: Layout, state: State, settings: Settings) -> None:
    scale = settings.scale
    for tyre, color in zip(layout.tyres, state.shown):
        ac.glColor4f(*color)
        ac.glQuad(*tyre)
    draw_slip_angles(layout.tyres, state.angles_shown, scale)
    draw_car_axis(layout.center, layout.reach, scale)
    draw_travel(layout.center, layout.reach, state.beta, state.beta_shown, scale)
    draw_buttons(layout.buttons, scale)


def place_widget(app: int, buttons: list, layout: Layout) -> None:
    ac.setSize(app, layout.width, layout.height)
    for button, (left, top) in zip(buttons, layout.buttons):
        ac.setPosition(button, left, top)
        ac.setSize(button, BUTTON, BUTTON)


# --- settings window ----------------------------------------------------------
def slip_range(settings: Settings) -> float:
    """Half-width of the plotted slip axis: a bit past the larger 'full' threshold."""
    return max(settings.lock[1], settings.spin[1]) / 100.0 * 1.25


def beta_range(settings: Settings) -> float:
    """Half-width of the plotted beta axis, deg: a bit past the 'full' threshold."""
    return settings.rotate[1] * 1.25


def plot_x(value: float, half_range: float) -> float:
    return remap(value, -half_range, half_range, PLOT_X, PLOT_X + PLOT_WIDTH)


def column_value(column: int, half_range: float) -> float:
    """Value at the centre of pixel column 0..PLOT_WIDTH-1 of the plot."""
    return remap(column + 0.5, 0, PLOT_WIDTH, -half_range, half_range)


def draw_curve(top: float, colors: list, ticks: list) -> None:
    """One 1px quad per colour, then a white tick at each x in ticks."""
    for column, color in enumerate(colors):
        ac.glColor4f(*color)
        ac.glQuad(PLOT_X + column, top, 1, CURVE_HEIGHT)
    ac.glColor4f(*WHITE)
    for tick_x in ticks:
        ac.glQuad(tick_x - 0.5, top - 4, 1, CURVE_HEIGHT + 8)


def draw_live_row(top: float, marker_x: float, color: tuple) -> None:
    """Live value marker on the curve's axis, and the colour the widget shows right now."""
    ac.glColor4f(*FAINT)
    ac.glQuad(PLOT_X, top + ROW_HEIGHT / 2 - 1, PLOT_WIDTH, 2)
    ac.glColor4f(*WHITE)
    ac.glQuad(marker_x - 2, top + 3, 4, ROW_HEIGHT - 6)
    ac.glColor4f(*color)
    ac.glQuad(SWATCH_X, top + 3, 20, ROW_HEIGHT - 6)


def draw_settings(state: State, settings: Settings) -> None:
    half = slip_range(settings)
    colors = [slip_color(column_value(column, half), settings) for column in range(PLOT_WIDTH)]
    ticks = [0.0] + [-limit / 100.0 for limit in settings.lock] + \
            [limit / 100.0 for limit in settings.spin]
    draw_curve(SLIP_Y, colors, [plot_x(tick, half) for tick in ticks])
    for index in range(4):
        draw_live_row(ROW_Y + index * ROW_HEIGHT, plot_x(state.slips[index], half),
                      state.shown[index])

    half = settings.angle[1] * 1.25
    colors = [angle_color(column_value(column, half), settings) for column in range(PLOT_WIDTH)]
    ticks = [0.0] + [side * limit for limit in settings.angle for side in (-1, 1)]
    draw_curve(ANGLE_Y, colors, [plot_x(tick, half) for tick in ticks])
    for index in range(4):
        draw_live_row(ANGLE_ROW_Y + index * ROW_HEIGHT, plot_x(state.angles[index], half),
                      state.angles_shown[index])

    half = beta_range(settings)
    colors = [beta_color(column_value(column, half), settings) for column in range(PLOT_WIDTH)]
    ticks = [0.0] + [side * limit for limit in settings.rotate for side in (-1, 1)]
    draw_curve(BETA_Y, colors, [plot_x(tick, half) for tick in ticks])
    draw_live_row(BETA_ROW_Y, plot_x(state.beta, half), state.beta_shown)


def settings_layout() -> list:
    """Every settings control as a Label or Spinner. Live labels have text None:
    render_settings fills them."""
    controls = [
        Label("h_signals", "SIGNALS  ac.getCarState(focused car, ...), read-only", 10, 35),
        Label("speed", None, 10, 55),
        # tyre slip: signal name, axis labels, curve (GL), one live row per wheel
        Label("h_slip", "acsys.CS.SlipRatio", 10, SLIP_Y - 35),
        Label("ax_lock", "lock  <", PLOT_X, SLIP_Y - 20, 11),
        Label("ax_slip0", "0", PLOT_X + PLOT_WIDTH / 2 - 3, SLIP_Y - 20, 11),
        Label("ax_spin", ">  spin", PLOT_X + PLOT_WIDTH - 40, SLIP_Y - 20, 11),
    ]
    for index in range(4):
        controls.append(Label("wheel{}".format(index), None, 10, ROW_Y + index * ROW_HEIGHT + 2))
    controls += [
        Label("h_angle", "acsys.CS.SlipAngle", 10, ANGLE_Y - 35),
        Label("ax_angle_left", "left  <", PLOT_X, ANGLE_Y - 20, 11),
        Label("ax_angle0", "0", PLOT_X + PLOT_WIDTH / 2 - 3, ANGLE_Y - 20, 11),
        Label("ax_angle_right", ">  right", PLOT_X + PLOT_WIDTH - 42, ANGLE_Y - 20, 11),
    ]
    for index in range(4):
        controls.append(Label("angle{}".format(index), None, 10,
                              ANGLE_ROW_Y + index * ROW_HEIGHT + 2))
    # rotation: same pattern
    controls += [
        Label("velocity", None, 10, BETA_Y - 35),
        Label("ax_left", "left  <", PLOT_X, BETA_Y - 20, 11),
        Label("ax_beta0", "0", PLOT_X + PLOT_WIDTH / 2 - 3, BETA_Y - 20, 11),
        Label("ax_right", ">  right", PLOT_X + PLOT_WIDTH - 42, BETA_Y - 20, 11),
        Label("beta", None, 10, BETA_ROW_Y + 2),
    ]
    for index, text in enumerate(RULES):
        controls.append(Label("rule{}".format(index), text, 10, RULES_Y + index * 17, 11))
    controls.append(Label("h_thresholds",
                          "THRESHOLDS  lock, spin: % of |SlipRatio|   rotate, angle: deg", 10,
                          THRESHOLDS_Y))
    for index, name in enumerate(("start", "full")):
        controls.append(Label("h_column{}".format(index), name, 110 + index * 100,
                              THRESHOLDS_Y + 18, 11))
    for row, kind in enumerate(("lock", "spin", "rotate", "angle")):
        row_top = THRESHOLDS_Y + 35 + row * 26
        controls.append(Label("h_" + kind, kind, 10, row_top + 2))
        for index in range(2):
            controls.append(Spinner("{}.{}".format(kind, index), 110 + index * 100, row_top,
                                    index, 99 + index))
    row_top = THRESHOLDS_Y + 35 + 4 * 26 + 4
    controls += [
        Label("h_min_speed", "min speed km/h", 10, row_top + 2),
        Spinner("min_speed", 110, row_top, 0, 100),
        Label("h_hold", "hold ms", 210, row_top + 2),
        Spinner("hold_ms", 310, row_top, 0, 1000, 10),
        Label("file", None, 10, row_top + 30, 11),
    ]
    return controls


def live_text(state: State, status: str) -> dict:
    """Text of the live labels (text None in settings_layout)."""
    texts = {"speed": "acsys.CS.SpeedKMH   {:.1f} km/h".format(state.speed),
             "velocity": "acsys.CS.LocalVelocity   x {:+.2f}  z {:+.2f} m/s".format(
                 state.velocity[0], state.velocity[2]),
             "beta": "beta  {:+.1f}".format(state.beta),
             "file": "settings.json  " + status[:70]}
    for index, (name, slip) in enumerate(zip(WHEELS, state.slips)):
        texts["wheel{}".format(index)] = "{}  {:+.3f}".format(name, slip)
    for index, (name, angle) in enumerate(zip(WHEELS, state.angles)):
        texts["angle{}".format(index)] = "{}  {:+.1f} deg".format(name, angle)
    return texts


def create_controls(window: int, layout: list, settings: Settings, listeners: list) -> dict:
    """Create every control in layout -> {key: control id}. Spinner listeners are appended
    to listeners: AC doesn't keep a reference, and a freed lambda crashes AC."""
    controls = {}
    for spec in layout:
        if isinstance(spec, Label):
            control = ac.addLabel(window, spec.text or "")
            ac.setFontSize(control, spec.size)
        else:
            control = ac.addSpinner(window, "")
            ac.setSize(control, *SPINNER_SIZE)
            ac.setRange(control, spec.low, spec.high)
            ac.setStep(control, spec.step)
            ac.setValue(control, spinner_value(settings, spec.key))
            listener = lambda value, key=spec.key: on_spinner(key, value)
            listeners.append(listener)
            ac.addOnValueChangeListener(control, listener)
        ac.setPosition(control, spec.left, spec.top)
        controls[spec.key] = control
    return controls


def write_spinners(controls: dict, settings: Settings) -> None:
    for spec in settings_layout():
        if isinstance(spec, Spinner):
            ac.setValue(controls[spec.key], spinner_value(settings, spec.key))


def log(message: str) -> None:
    ac.log("WheelLock: " + message)
    ac.console("WheelLock: " + message)


# --- app state: changed only by the AC callbacks below -----------------------
ui = Ui(app=0, buttons=[], settings_window=0, controls={}, listeners=[],
        settings_open=False, quiet=False)
settings = DEFAULTS
status = ""
state = IDLE


def persist() -> None:
    global status
    status = save_settings(settings, SETTINGS_FILE)
    if status.startswith("NOT"):
        log("settings.json " + status)


def render_widget(delta_time: float) -> None:
    # AC restores the backdrop on hover/drag; clear it every frame
    ac.setBackgroundOpacity(ui.app, 0)
    for button in ui.buttons:
        ac.setBackgroundOpacity(button, 0)
    draw_widget(geometry(settings.scale), state, settings)


def render_settings(delta_time: float) -> None:
    # AC calls this only while the settings window is visible: live labels need no open flag
    for key, text in live_text(state, status).items():
        ac.setText(ui.controls[key], text)
    draw_settings(state, settings)


def change_scale(step: int) -> None:
    global settings
    settings = with_scale(settings, step)
    place_widget(ui.app, ui.buttons, geometry(settings.scale))
    persist()


def on_settings_click(*args: object) -> None:
    ui.settings_open = not ui.settings_open
    ac.setVisible(ui.settings_window, 1 if ui.settings_open else 0)


def on_shrink_click(*args: object) -> None:
    change_scale(-1)


def on_grow_click(*args: object) -> None:
    change_scale(1)


# AC's own taskbar/close button can also show or hide the settings: keep the flag in sync
def on_settings_shown(*args: object) -> None:
    ui.settings_open = True


def on_settings_hidden(*args: object) -> None:
    ui.settings_open = False


def on_spinner(key: str, value: float) -> None:
    """User edit of a spinner. AC also fires this from inside ac.setValue/ac.setRange,
    so code writes set ui.quiet and are ignored here."""
    global settings
    if ui.quiet:
        return
    settings = with_spinner(settings, key, value)
    ui.quiet = True
    try:
        write_spinners(ui.controls, settings)  # a threshold edit may push its pair
    finally:
        ui.quiet = False
    persist()


def acMain(ac_version: str) -> str:
    global settings, status
    settings, status = load_settings(SETTINGS_FILE)
    log("settings.json " + status)

    ui.app = app = ac.newApp("WheelLock")
    ac.setTitle(app, "")
    ac.setIconPosition(app, 0, -10000)
    ac.drawBorder(app, 0)
    ac.setBackgroundTexture(app, BACKGROUND)
    for listener in (on_settings_click, on_shrink_click, on_grow_click):
        button = ac.addButton(app, "")
        ac.drawBorder(button, 0)
        ac.addOnClickedListener(button, listener)
        ui.buttons.append(button)
    place_widget(app, ui.buttons, geometry(settings.scale))
    ac.addRenderCallback(app, render_widget)

    ui.settings_window = window = ac.newApp("WheelLock Settings")
    ac.setTitle(window, "WheelLock Settings")
    ac.setSize(window, *SETTINGS_SIZE)
    ac.setVisible(window, 0)
    ac.addRenderCallback(window, render_settings)
    ac.addOnAppActivatedListener(window, on_settings_shown)
    ac.addOnAppDismissedListener(window, on_settings_hidden)
    ui.quiet = True  # setRange/setValue fire listeners; nothing here is a user edit
    try:
        ui.controls = create_controls(window, settings_layout(), settings, ui.listeners)
    finally:
        ui.quiet = False
    return "WheelLock"


def acUpdate(delta_time: float) -> None:
    global state
    car = ac.getFocusedCar()
    state = advance(state,
                    ac.getCarState(car, acsys.CS.SpeedKMH),
                    ac.getCarState(car, acsys.CS.SlipRatio),
                    ac.getCarState(car, acsys.CS.SlipAngle),
                    ac.getCarState(car, acsys.CS.LocalVelocity),
                    delta_time, settings)

# Wheel-slip widget for Assetto Corsa: four tyres, colour = each tyre's slip ratio as AC's
# physics reports it (acsys.CS.SlipRatio). Negative = locking, positive = spinning.
# A second window ("WheelLock Settings") shows the live signals, the colour curve and the
# thresholds, and lets you edit them. Open it with the sliders button on the widget.
# Runs in AC's embedded Python 3.3: no f-strings, no third-party imports.
# Everything here hot-reloads: WheelLock.py re-imports this file when it changes on disk.
import json
import math
import os
import ac
import acsys

APP_DIR = os.path.dirname(__file__)
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
# AC resets window opacity while it's dragged/hovered; a transparent texture keeps it invisible then.
BG_TEXTURE = "apps/python/WheelLock/img/bg.png"

# --- settings (edited in the settings window, saved to settings.json) ---------
# lock/spin: [start, full] in % of |SlipRatio|, start < full.
DEFAULTS = {"scale": 1.0, "lock": [2, 10], "spin": [2, 10], "min_speed": 10, "hold_ms": 120}
cfg = {}

# --- colours (rgba) -----------------------------------------------------------
GREY = (0.25, 0.25, 0.25, 0.8)  # |slip| <= start, or car slower than min speed
PURPLE = (0.6, 0.3, 1.0, 1.0)  # lock at full
AMBER = (1.0, 0.69, 0.0, 1.0)  # spin at full
WHITE = (1.0, 1.0, 1.0, 1.0)
BTN_ON = (1.0, 1.0, 1.0, 0.7)
BTN_OFF = (1.0, 1.0, 1.0, 0.2)  # at min/max scale

# --- widget layout (px) -------------------------------------------------------
TYRE_W, TYRE_H, TRACK, BASE = 16, 26, 30, 18  # at scale 1.0: tyre size, left-right gap, front-rear gap
SCALES = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
BAR = 24     # top strip kept free of tyres: AC/CSP draw the pin there, our buttons sit beside it
PIN_W = 28   # right end of BAR reserved for CSP's pin button
BTN = 16     # button size

# --- settings window layout (px) ----------------------------------------------
SET_W, SET_H = 430, 470
PLOT_X, PLOT_W = 110, 270        # slip axis of the curve and the wheel rows
CURVE_Y, CURVE_H = 110, 20
ROW_Y, ROW_H = 140, 20           # FL, FR, RL, RR rows below the curve
SWATCH_X = PLOT_X + PLOT_W + 12  # colour the widget is showing right now
WHEELS = ("FL", "FR", "RL", "RR")

# Exactly what update() does, shown in the settings window.
RULES = (
    "every frame, focused car:",
    "  SpeedKMH < min speed            -> all tyres grey",
    "  SlipRatio < 0 (lock):  |s| <= start grey, start..full grey->purple, >= full purple",
    "  SlipRatio > 0 (spin):  |s| <= start grey, start..full grey->amber,  >= full amber",
    "  |s| >= full and speed >= min -> that colour stays for hold ms",
)

ui = None                                # loader-owned dict: control ids survive reloads
speed = 0.0
slip = [0.0, 0.0, 0.0, 0.0]              # raw CS.SlipRatio
shown = [GREY] * 4                       # colour on screen per tyre
held = [(0.0, GREY) for _ in range(4)]   # (seconds left, colour) per tyre
geo = None


# --- model --------------------------------------------------------------------
def lerp(c0, c1, t):
    return tuple(a + (b - a) * t for a, b in zip(c0, c1))


def colour(s):
    """SlipRatio -> rgba, piecewise linear through the thresholds in cfg."""
    start, full = [x / 100.0 for x in cfg["lock" if s < 0 else "spin"]]
    hot = PURPLE if s < 0 else AMBER
    a = abs(s)
    if a <= start:
        return GREY
    if a < full:
        return lerp(GREY, hot, (a - start) / (full - start))
    return hot


def is_full(s):
    return abs(s) * 100 >= cfg["lock" if s < 0 else "spin"][1]


def step(speed_kmh, ratios, dt):
    """Advance one frame; returns the colour of each tyre (FL, FR, RL, RR)."""
    out = []
    for i, s in enumerate(ratios):
        c = GREY if speed_kmh < cfg["min_speed"] else colour(s)
        if speed_kmh >= cfg["min_speed"] and is_full(s):
            held[i] = (cfg["hold_ms"] / 1000.0, c)
        elif held[i][0] > 0:
            held[i] = (held[i][0] - dt, held[i][1])
            if held[i][0] > 0:
                c = held[i][1]
        out.append(c)
    return out


# --- settings -----------------------------------------------------------------
def load_cfg():
    cfg.clear()
    cfg.update(json.loads(json.dumps(DEFAULTS)))  # deep copy
    try:
        with open(SETTINGS_FILE) as f:
            saved = json.load(f)
        for k in DEFAULTS:
            if k in saved:
                cfg[k] = saved[k]
        if cfg["scale"] not in SCALES:
            cfg["scale"] = DEFAULTS["scale"]
        for k in ("lock", "spin"):
            t = cfg[k]
            if not (len(t) == 2 and 0 <= t[0] < t[1] <= 100):
                cfg[k] = list(DEFAULTS[k])
    except (IOError, ValueError, TypeError, KeyError):
        pass


def save_cfg():
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(cfg, f, indent=1)
    except IOError:
        pass


def set_threshold(kind, j, v):
    """Set lock/spin threshold j (0 start, 1 full) to v %, pushing the other so start < full."""
    t = cfg[kind]
    t[j] = max(j, min(99 + j, int(v)))
    if j == 0:
        t[1] = max(t[1], t[0] + 1)
    else:
        t[0] = min(t[0], t[1] - 1)
    for k in range(2):
        ac.setValue(ui[kind][k], t[k])
    save_cfg()


def set_value(key, v):
    cfg[key] = int(v)
    save_cfg()


# --- widget window ------------------------------------------------------------
def geometry(k):
    """Window size, tyre rects (FL, FR, RL, RR) and button positions at scale k."""
    w, h = int(TYRE_W * k), int(TYRE_H * k)
    track, base = int(TRACK * k), int(BASE * k)
    car_w = w * 2 + track
    win_w = max(car_w, PIN_W + 3 * (BTN + 4) + 4)
    x0 = (win_w - car_w) // 2
    rects = [(x, y, w, h) for y in (BAR, BAR + h + base) for x in (x0, x0 + w + track)]
    bx = win_w - PIN_W - 3 * (BTN + 4)
    by = (BAR - BTN) // 2
    btns = [(bx + i * (BTN + 4), by) for i in range(3)]  # settings, collapse, expand
    return win_w, BAR + h * 2 + base, rects, btns


def apply_layout():
    global geo
    geo = geometry(cfg["scale"])
    win_w, win_h, _, btns = geo
    ac.setSize(ui["app"], win_w, win_h)
    for b, (x, y) in zip(ui["buttons"], btns):
        ac.setPosition(b, x, y)
        ac.setSize(b, BTN, BTN)


def set_scale(step_):
    i = max(0, min(len(SCALES) - 1, SCALES.index(cfg["scale"]) + step_))
    cfg["scale"] = SCALES[i]
    apply_layout()
    save_cfg()


def toggle_settings(*args):
    ui["settings_open"] = not ui["settings_open"]
    ac.setVisible(ui["settings"], 1 if ui["settings_open"] else 0)


def arrow(x0, y0, x1, y1, t):
    """Filled arrow from (x0, y0) to head at (x1, y1), shaft thickness t."""
    dx, dy = x1 - x0, y1 - y0
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n
    px, py = -uy, ux
    bx, by = x1 - ux * t * 2.2, y1 - uy * t * 2.2  # head base
    s, hw = t / 2, t * 1.6
    ac.glBegin(acsys.GL.Quads)
    for vx, vy in ((x0 + px * s, y0 + py * s), (bx + px * s, by + py * s),
                   (bx - px * s, by - py * s), (x0 - px * s, y0 - py * s)):
        ac.glVertex2f(vx, vy)
    ac.glEnd()
    ac.glBegin(acsys.GL.Triangles)
    for vx, vy in ((x1, y1), (bx + px * hw, by + py * hw), (bx - px * hw, by - py * hw)):
        ac.glVertex2f(vx, vy)
    ac.glEnd()


def draw_resize_icon(x, y, outward):
    """Two diagonal arrows: pointing to the corners (expand) or to the centre (collapse)."""
    m, g, t = BTN * 0.12, BTN * 0.1, 1.6
    c = BTN / 2.0
    for sx in (-1, 1):
        corner = (x + c + sx * (c - m), y + c + sx * (c - m))
        mid = (x + c + sx * g, y + c + sx * g)
        a, b = (mid, corner) if outward else (corner, mid)
        arrow(a[0], a[1], b[0], b[1], t)


def draw_sliders_icon(x, y):
    """Three lines with knobs: settings."""
    for i, kx in enumerate((0.3, 0.7, 0.45)):
        ly = y + BTN * (0.25 + 0.25 * i)
        ac.glQuad(x + 1, ly - 0.75, BTN - 2, 1.5)
        ac.glQuad(x + BTN * kx - 2, ly - 2.5, 4, 5)


def render(deltaT):
    app = ui["app"]
    # AC restores the backdrop on hover/drag; clear it every frame
    ac.setBackgroundOpacity(app, 0)
    for b in ui["buttons"]:
        ac.setBackgroundOpacity(b, 0)
    _, _, rects, btns = geo
    for (x, y, w, h), c in zip(rects, shown):
        ac.glColor4f(*c)
        ac.glQuad(x, y, w, h)
    i = SCALES.index(cfg["scale"])
    ac.glColor4f(*BTN_ON)
    draw_sliders_icon(*btns[0])
    for (x, y), outward, enabled in zip(btns[1:], (False, True), (i > 0, i < len(SCALES) - 1)):
        ac.glColor4f(*(BTN_ON if enabled else BTN_OFF))
        draw_resize_icon(x, y, outward)


# --- settings window ----------------------------------------------------------
def axis_range():
    """Half-width of the plotted slip axis: a bit past the larger 'full' threshold."""
    return max(cfg["lock"][1], cfg["spin"][1]) / 100.0 * 1.25


def to_x(s):
    r = axis_range()
    return PLOT_X + (max(-r, min(r, s)) + r) / (2 * r) * PLOT_W


def render_settings(deltaT):
    # curve: the exact colour() for every pixel column of the slip axis
    r = axis_range()
    for px in range(PLOT_W):
        ac.glColor4f(*colour(-r + (px + 0.5) / PLOT_W * 2 * r))
        ac.glQuad(PLOT_X + px, CURVE_Y, 1, CURVE_H)
    ac.glColor4f(*WHITE)
    ticks = [0.0] + [-x / 100.0 for x in cfg["lock"]] + [x / 100.0 for x in cfg["spin"]]
    for s in ticks:
        ac.glQuad(to_x(s) - 0.5, CURVE_Y - 4, 1, CURVE_H + 8)
    # one row per wheel: live SlipRatio marker on the same axis, and the colour on screen
    for i in range(4):
        y = ROW_Y + i * ROW_H
        ac.glColor4f(1, 1, 1, 0.15)
        ac.glQuad(PLOT_X, y + ROW_H / 2 - 1, PLOT_W, 2)
        ac.glColor4f(*WHITE)
        ac.glQuad(to_x(slip[i]) - 2, y + 3, 4, ROW_H - 6)
        ac.glColor4f(*shown[i])
        ac.glQuad(SWATCH_X, y + 3, 20, ROW_H - 6)


def label(text, x, y, size=13):
    l = ac.addLabel(ui["settings"], text)
    ac.setPosition(l, x, y)
    ac.setFontSize(l, size)
    return l


def spinner(x, y, lo, hi, value, step_, on_change):
    s = ac.addSpinner(ui["settings"], "")
    ac.setPosition(s, x, y)
    ac.setSize(s, 90, 20)
    ac.setRange(s, lo, hi)
    ac.setStep(s, step_)
    ac.setValue(s, value)
    ac.addOnValueChangeListener(s, keep(on_change))
    return s


def keep(fn):
    """AC stores callbacks without taking a reference: an unreferenced lambda gets freed and
    AC then calls freed memory (native crash in PythonForm::render). ui lives all session."""
    ui["callbacks"].append(fn)
    return fn


def build(ui_):
    """Create both windows and all controls. Runs once per session; callbacks are thin
    wrappers that look up the current module function, so they keep working after reloads."""
    global ui
    ui = ui_
    ui_["callbacks"] = []
    g = globals()
    ui_["app"] = app = ac.newApp("WheelLock")
    ui_["buttons"] = []
    for name, args in (("toggle_settings", ()), ("set_scale", (-1,)), ("set_scale", (1,))):
        b = ac.addButton(app, "")
        ac.addOnClickedListener(b, keep(lambda *a, n=name, p=args: g[n](*p)))
        ui_["buttons"].append(b)
    ac.addRenderCallback(app, keep(lambda dt: g["render"](dt)))

    ui_["settings"] = win = ac.newApp("WheelLock Settings")
    ui_["settings_open"] = False
    ac.setSize(win, SET_W, SET_H)
    ac.setVisible(win, 0)
    ac.addRenderCallback(win, keep(lambda dt: g["render_settings"](dt)))
    # AC's own taskbar/close button can also show or hide it: keep our flag in sync
    ac.addOnAppActivatedListener(win, keep(lambda *a: ui_.update(settings_open=True)))
    ac.addOnAppDismissedListener(win, keep(lambda *a: ui_.update(settings_open=False)))

    label("SIGNALS  ac.getCarState(focused car, ...), read-only", 10, 35)
    ui_["speed"] = label("", 10, 55)
    label("acsys.CS.SlipRatio", 10, 75)
    label("lock  <", PLOT_X, 90, 11)
    label("0", to_x(0) - 3, 90, 11)
    label(">  spin", PLOT_X + PLOT_W - 40, 90, 11)
    ui_["wheel"] = [label("", 10, ROW_Y + i * ROW_H + 2) for i in range(4)]
    for i, text in enumerate(RULES):
        label(text, 10, 230 + i * 17, 11)
    label("THRESHOLDS  % of |SlipRatio|", 10, 340)
    for j, name in enumerate(("start", "full")):
        label(name, 110 + j * 100, 358, 11)
    for row, kind in enumerate(("lock", "spin")):
        y = 375 + row * 26
        label(kind, 10, y)
        ui_[kind] = [spinner(110 + j * 100, y, j, 99 + j, cfg[kind][j], 1,
                             lambda v, k=kind, j=j: g["set_threshold"](k, j, v))
                     for j in range(2)]
    label("min speed km/h", 10, 432)
    spinner(110, 430, 0, 100, cfg["min_speed"], 1, lambda v: g["set_value"]("min_speed", v))
    label("hold ms", 210, 432)
    spinner(310, 430, 0, 1000, cfg["hold_ms"], 10, lambda v: g["set_value"]("hold_ms", v))


def init(ui_):
    """Runs at start and after every hot reload. ui_ is owned by WheelLock.py."""
    global ui
    load_cfg()
    if not ui_:
        build(ui_)
    ui = ui_
    app = ui["app"]
    ac.setTitle(app, "")
    ac.setIconPosition(app, 0, -10000)
    ac.drawBorder(app, 0)
    ac.setBackgroundTexture(app, BG_TEXTURE)
    for b in ui["buttons"]:
        ac.drawBorder(b, 0)
    ac.setTitle(ui["settings"], "WheelLock Settings")
    apply_layout()


def update(deltaT):
    global speed
    car = ac.getFocusedCar()
    speed = ac.getCarState(car, acsys.CS.SpeedKMH)
    slip[:] = ac.getCarState(car, acsys.CS.SlipRatio)
    shown[:] = step(speed, slip, deltaT)
    if ui["settings_open"]:
        ac.setText(ui["speed"], "acsys.CS.SpeedKMH   {:.1f} km/h".format(speed))
        for l, name, s in zip(ui["wheel"], WHEELS, slip):
            ac.setText(l, "{}  {:+.3f}".format(name, s))

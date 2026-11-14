# Wheel-slip widget for Assetto Corsa: four tyres, colour = each tyre's slip ratio as AC's
# physics reports it (acsys.CS.SlipRatio). Negative = locking, positive = spinning.
# Dotted line = the car's own axis, nose to tail. Solid line with the arrow head = the
# direction of travel through the car centre (body slip angle). Lines together = car goes
# where it points; solid line tilted = car is rotating/sliding, head points the way to
# countersteer. Colour works like the tyres: grey up to start, grey->red to full.
# A second window ("WheelLock Settings") shows the live signals, the colour curve and the
# thresholds, and lets you edit them. Open it with the sliders button on the widget.
# Runs in AC's embedded Python 3.3: no f-strings, no third-party imports.
# Everything here hot-reloads: WheelLock.py re-imports this file when it changes on disk.
import json
import math
import os
import time
import ac
import acsys

APP_DIR = os.path.dirname(__file__)
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
# AC resets window opacity while it's dragged/hovered; a transparent texture keeps it invisible then.
BG_TEXTURE = "apps/python/WheelLock/img/bg.png"

# --- settings (edited in the settings window, saved to settings.json) ---------
# lock/spin: [start, full] in % of |SlipRatio|, start < full.
# rotate: [start, full] in degrees of body slip angle. Defaults from recorded laps
# (mp4-12c GT3, Laguna Seca): grip stays under 3 deg 90% of the time; once a slide passes
# 8 deg 28% of them ended in a spin, and the spins only got countersteer at 10-14 deg.
DEFAULTS = {"scale": 1.0, "lock": [2, 10], "spin": [2, 10], "rotate": [3, 8],
            "min_speed": 10, "hold_ms": 120}
cfg = {}

# --- colours (rgba) -----------------------------------------------------------
GREY = (0.25, 0.25, 0.25, 0.8)  # |slip| <= start, or car slower than min speed
PURPLE = (0.6, 0.3, 1.0, 1.0)  # lock at full
AMBER = (1.0, 0.69, 0.0, 1.0)  # spin at full
RED = (1.0, 0.2, 0.2, 1.0)     # rotation at full
WHITE = (1.0, 1.0, 1.0, 1.0)
AXIS = (1.0, 1.0, 1.0, 0.3)    # dotted car axis on the widget: a faint reference
BTN_ON = (1.0, 1.0, 1.0, 0.7)
BTN_OFF = (1.0, 1.0, 1.0, 0.2)  # at min/max scale

# --- widget layout (px) -------------------------------------------------------
TYRE_W, TYRE_H, TRACK, BASE = 16, 26, 30, 18  # at scale 1.0: tyre size, left-right gap, front-rear gap
SCALES = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
BAR = 24     # top strip kept free of tyres: AC/CSP draw the pin there, our buttons sit beside it
PIN_W = 28   # right end of BAR reserved for CSP's pin button
BTN = 16     # button size

# --- settings window layout (px) ----------------------------------------------
SET_W, SET_H = 430, 630
PLOT_X, PLOT_W = 110, 270        # slip axis of the curve and the wheel rows
CURVE_Y, CURVE_H = 110, 20
ROW_Y, ROW_H = 140, 20           # FL, FR, RL, RR rows below the curve
SWATCH_X = PLOT_X + PLOT_W + 12  # colour the widget is showing right now
ROT_Y = 270                      # rotation curve (same spacing as CURVE_Y to its labels)
BETA_Y = ROT_Y + 30              # live beta row, like a wheel row under its curve
RULES_Y, THR_Y = 335, 460        # rules text, thresholds block
WHEELS = ("FL", "FR", "RL", "RR")

# Exactly what update() does, shown in the settings window.
RULES = (
    "every frame, focused car:",
    "  SpeedKMH < min speed            -> all tyres grey, arrow grey and straight up",
    "  SlipRatio < 0 (lock):  |s| <= start grey, start..full grey->purple, >= full purple",
    "  SlipRatio > 0 (spin):  |s| <= start grey, start..full grey->amber,  >= full amber",
    "  beta = atan2(-x, z) of LocalVelocity, + = travelling right of the nose, arrow tilts",
    "  beta (rotate):         |b| <= start grey, start..full grey->red,    >= full red",
    "  |value| >= full and speed >= min -> that colour stays for hold ms",
)

cfg_status = ""                          # last settings.json load/save result, shown in settings
ui = None                                # loader-owned dict: control ids survive reloads
speed = 0.0
slip = [0.0, 0.0, 0.0, 0.0]              # raw CS.SlipRatio
shown = [GREY] * 4                       # colour on screen per tyre
held = [(0.0, GREY) for _ in range(4)]   # (seconds left, colour) per tyre
beta = 0.0                               # body slip angle, deg, + = travel right of nose
vel = (0.0, 0.0, 0.0)                    # raw CS.LocalVelocity
rot_shown = GREY
rot_held = 0.0                           # seconds the red stays
geo = None


# --- model --------------------------------------------------------------------
def lerp(c0, c1, t):
    return tuple(a + (b - a) * t for a, b in zip(c0, c1))


def ramp(a, start, full, hot):
    """Magnitude -> rgba: grey up to start, linear grey->hot to full, hot beyond."""
    if a <= start:
        return GREY
    if a < full:
        return lerp(GREY, hot, (a - start) / float(full - start))
    return hot


def colour(s):
    """SlipRatio -> rgba through the lock/spin thresholds (% of |SlipRatio|)."""
    return ramp(abs(s) * 100, *cfg["lock" if s < 0 else "spin"],
                hot=PURPLE if s < 0 else AMBER)


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


def body_slip(v, speed_kmh):
    """Angle (deg) between where the car points and where it travels; + = travel to the right.
    AC's local frame is y up, z forward, x left, so right = -x (checked against tyre contact
    points in recordings; in slides drivers countersteer to the side this points)."""
    if speed_kmh < cfg["min_speed"]:
        return 0.0  # direction of a near-zero velocity is noise
    return math.degrees(math.atan2(-v[0], v[2]))


def rot_colour(b):
    """Body slip angle (deg) -> rgba through the rotate thresholds, same ramp as the tyres."""
    return ramp(abs(b), *cfg["rotate"], hot=RED)


def rot_step(b, dt):
    """Arrow colour for this frame; red stays for hold ms so a short snap is still seen.
    No look-ahead on the beta rate: in recordings spins (11-62 deg/s) and saves (4-87 deg/s)
    overlap, so prediction only added false reds."""
    global rot_held
    c = rot_colour(b)
    if abs(b) >= cfg["rotate"][1]:
        rot_held = cfg["hold_ms"] / 1000.0
    elif rot_held > 0:
        rot_held -= dt
        if rot_held > 0:
            c = RED
    return c


# --- settings -----------------------------------------------------------------
def log(msg):
    ac.log("WheelLock: " + msg)
    ac.console("WheelLock: " + msg)


def valid(k, v):
    """Is v an acceptable saved value for setting k?"""
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
    if k == "scale":
        return v in SCALES
    if k in ("lock", "spin", "rotate"):
        return isinstance(v, list) and len(v) == 2 and all(map(num, v)) and 0 <= v[0] < v[1] <= 100
    if k == "min_speed":
        return num(v) and 0 <= v <= 100
    if k == "hold_ms":
        return num(v) and 0 <= v <= 1000
    return False


def load_cfg():
    """Defaults, overlaid key by key with every valid value in settings.json."""
    global cfg_status
    cfg.clear()
    cfg.update(json.loads(json.dumps(DEFAULTS)))  # deep copy
    try:
        with open(SETTINGS_FILE) as f:
            saved = json.load(f)
    except IOError:
        cfg_status = "no file yet, defaults"
        return
    except ValueError as e:
        cfg_status = "unreadable, defaults: {}".format(e)
        log("settings.json " + cfg_status)
        return
    if not isinstance(saved, dict):
        saved = {}
    bad = sorted(k for k in DEFAULTS if k in saved and not valid(k, saved[k]))
    for k in DEFAULTS:
        if k in saved and k not in bad:
            cfg[k] = saved[k]
    cfg_status = "loaded" + (", reset to default: " + ", ".join(bad) if bad else "")
    if bad:
        log("settings.json " + cfg_status)


def save_cfg():
    """Write via a temp file and os.replace: a crash mid-write can't leave a half file
    that the next load would throw away."""
    global cfg_status
    tmp = SETTINGS_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(cfg, f, indent=1, sort_keys=True)
        os.replace(tmp, SETTINGS_FILE)
        cfg_status = "saved " + time.strftime("%H:%M:%S")
    except (IOError, OSError) as e:
        cfg_status = "NOT SAVED: {}".format(e)
        log("settings.json " + cfg_status)


def set_threshold(kind, j, v):
    """Set lock/spin threshold j (0 start, 1 full) to v %, pushing the other so start < full."""
    t = cfg[kind]
    t[j] = max(j, min(99 + j, int(v)))
    if j == 0:
        t[1] = max(t[1], t[0] + 1)
    else:
        t[0] = min(t[0], t[1] - 1)
    for k in range(2):
        set_spinner("{}.{}".format(kind, k), t[k])
    save_cfg()


def set_spinner(key, v):
    """Write a spinner without running its listener. AC fires the change listener from
    inside ac.setValue/ac.setRange, so code writes would re-enter on_spin."""
    ui["quiet"] = True
    try:
        ac.setValue(ui["ctl"][key], v)
    finally:
        ui["quiet"] = False


def on_spin(key, v):
    """Spinner key 'lock.0' -> threshold lock start; 'min_speed' -> plain value.
    Only user edits get here: code writes go through set_spinner / sync_controls."""
    if ui.get("quiet"):
        return
    if "." in key:
        kind, j = key.split(".")
        set_threshold(kind, int(j), v)
    else:
        set_value(key, v)


def set_value(key, v):
    cfg[key] = int(v)
    save_cfg()


# --- widget window ------------------------------------------------------------
def geometry(k):
    """Window size, tyre rects (FL, FR, RL, RR), button positions and the travel arrow
    (centre x, centre y, length) at scale k."""
    w, h = int(TYRE_W * k), int(TYRE_H * k)
    track, base = int(TRACK * k), int(BASE * k)
    car_w = w * 2 + track
    reach = h + base / 2.0  # car centre to the front edge of the tyres
    win_w = max(car_w, int(2 * reach + 4 * k), PIN_W + 3 * (BTN + 4) + 4)
    x0 = (win_w - car_w) // 2
    rects = [(x, y, w, h) for y in (BAR, BAR + h + base) for x in (x0, x0 + w + track)]
    bx = win_w - PIN_W - 3 * (BTN + 4)
    by = (BAR - BTN) // 2
    btns = [(bx + i * (BTN + 4), by) for i in range(3)]  # settings, collapse, expand
    return win_w, BAR + h * 2 + base, rects, btns, (win_w / 2.0, BAR + reach, reach)


def apply_layout():
    global geo
    geo = geometry(cfg["scale"])
    win_w, win_h, _, btns, _ = geo
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
    _, _, rects, btns, (cx, cy, reach) = geo
    for (x, y, w, h), c in zip(rects, shown):
        ac.glColor4f(*c)
        ac.glQuad(x, y, w, h)
    # car axis: dotted, nose to tail, thin and faint, under the travel line
    k = cfg["scale"]
    ac.glColor4f(*AXIS)
    dash, gap, t = 3 * k, 3 * k, max(1.0, 0.75 * k)
    y = cy - reach
    while y < cy + reach:
        ac.glQuad(cx - t / 2, y, t, min(dash, cy + reach - y))
        y += dash + gap
    # travel line: solid, through the car centre, rotated by beta, head at the front end
    a = math.radians(max(-90.0, min(90.0, beta)))  # past 90 deg it's a spin; red says enough
    dx, dy = reach * math.sin(a), reach * math.cos(a)
    ac.glColor4f(*rot_shown)
    arrow(cx - dx, cy + dy, cx + dx, cy - dy, 3 * k)
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


def rot_range():
    """Half-width of the plotted beta axis, deg: a bit past the 'full' threshold."""
    return cfg["rotate"][1] * 1.25


def to_x(s, r=None):
    r = r or axis_range()
    return PLOT_X + (max(-r, min(r, s)) + r) / (2 * r) * PLOT_W


def plot(y, fn, r, ticks):
    """Colour curve: fn() for every pixel column of the axis -r..r, white tick per threshold."""
    for px in range(PLOT_W):
        ac.glColor4f(*fn(-r + (px + 0.5) / PLOT_W * 2 * r))
        ac.glQuad(PLOT_X + px, y, 1, CURVE_H)
    ac.glColor4f(*WHITE)
    for t in [0.0] + ticks:
        ac.glQuad(to_x(t, r) - 0.5, y - 4, 1, CURVE_H + 8)


def live_row(y, v, r, c):
    """Live value marker on the curve's axis, and the colour the widget shows right now."""
    ac.glColor4f(1, 1, 1, 0.15)
    ac.glQuad(PLOT_X, y + ROW_H / 2 - 1, PLOT_W, 2)
    ac.glColor4f(*WHITE)
    ac.glQuad(to_x(v, r) - 2, y + 3, 4, ROW_H - 6)
    ac.glColor4f(*c)
    ac.glQuad(SWATCH_X, y + 3, 20, ROW_H - 6)


def render_settings(deltaT):
    r = axis_range()
    plot(CURVE_Y, colour, r, [-x / 100.0 for x in cfg["lock"]] + [x / 100.0 for x in cfg["spin"]])
    for i in range(4):
        live_row(ROW_Y + i * ROW_H, slip[i], r, shown[i])
    r = rot_range()
    plot(ROT_Y, rot_colour, r, [sg * x for x in cfg["rotate"] for sg in (-1, 1)])
    live_row(BETA_Y, beta, r, rot_shown)


SPIN_W, SPIN_H = 90, 20


def layout():
    """Every settings control: key -> ("label", text, x, y, font size) or
    ("spin", x, y, lo, hi, step). Live labels have text None: update() fills them.
    Applied on every init, so a layout change here takes effect on hot reload."""
    L = {}

    def lab(key, text, x, y, size=13):
        L[key] = ("label", text, x, y, size)

    def spin(key, x, y, lo, hi, step_=1):
        L[key] = ("spin", x, y, lo, hi, step_)

    lab("h_signals", "SIGNALS  ac.getCarState(focused car, ...), read-only", 10, 35)
    lab("speed", None, 10, 55)
    # tyre slip: signal name, axis labels, curve (GL), one live row per wheel
    lab("h_slip", "acsys.CS.SlipRatio", 10, CURVE_Y - 35)
    lab("ax_lock", "lock  <", PLOT_X, CURVE_Y - 20, 11)
    lab("ax_slip0", "0", PLOT_X + PLOT_W / 2 - 3, CURVE_Y - 20, 11)
    lab("ax_spin", ">  spin", PLOT_X + PLOT_W - 40, CURVE_Y - 20, 11)
    for i in range(4):
        lab("wheel{}".format(i), None, 10, ROW_Y + i * ROW_H + 2)
    # rotation: same pattern
    lab("vel", None, 10, ROT_Y - 35)
    lab("ax_left", "left  <", PLOT_X, ROT_Y - 20, 11)
    lab("ax_rot0", "0", PLOT_X + PLOT_W / 2 - 3, ROT_Y - 20, 11)
    lab("ax_right", ">  right", PLOT_X + PLOT_W - 42, ROT_Y - 20, 11)
    lab("beta", None, 10, BETA_Y + 2)
    for i, text in enumerate(RULES):
        lab("rule{}".format(i), text, 10, RULES_Y + i * 17, 11)
    lab("h_thr", "THRESHOLDS  lock, spin: % of |SlipRatio|   rotate: deg", 10, THR_Y)
    for j, name in enumerate(("start", "full")):
        lab("h_col{}".format(j), name, 110 + j * 100, THR_Y + 18, 11)
    for row, kind in enumerate(("lock", "spin", "rotate")):
        y = THR_Y + 35 + row * 26
        lab("h_" + kind, kind, 10, y + 2)
        for j in range(2):
            spin("{}.{}".format(kind, j), 110 + j * 100, y, j, 99 + j)
    y = THR_Y + 35 + 3 * 26 + 4
    lab("h_min_speed", "min speed km/h", 10, y + 2)
    spin("min_speed", 110, y, 0, 100)
    lab("h_hold", "hold ms", 210, y + 2)
    spin("hold_ms", 310, y, 0, 1000, 10)
    lab("file", None, 10, y + 30, 11)
    return L


def spin_value(key):
    if "." in key:
        kind, j = key.split(".")
        return cfg[kind][int(j)]
    return cfg[key]


def sync_controls():
    """Create missing settings controls, place every control per layout(), hide stale ones.
    AC can't delete controls, so ids live in ui["ctl"] for the whole session."""
    g = globals()
    ctl = ui.setdefault("ctl", {})
    want = layout()
    ui["quiet"] = True  # setRange/setValue below fire listeners; nothing here is a user edit
    try:
        place(ctl, want, g)
    finally:
        ui["quiet"] = False
    for key in ctl:
        if key not in want:
            ac.setVisible(ctl[key], 0)


def place(ctl, want, g):
    for key, spec in sorted(want.items()):
        if spec[0] == "label":
            _, text, x, y, size = spec
            if key not in ctl:
                ctl[key] = ac.addLabel(ui["settings"], text or "")
            if text is not None:
                ac.setText(ctl[key], text)
            ac.setFontSize(ctl[key], size)
        else:
            _, x, y, lo, hi, step_ = spec
            if key not in ctl:
                ctl[key] = ac.addSpinner(ui["settings"], "")
                ac.addOnValueChangeListener(ctl[key], keep(lambda v, k=key: g["on_spin"](k, v)))
            ac.setSize(ctl[key], SPIN_W, SPIN_H)
            ac.setRange(ctl[key], lo, hi)
            ac.setStep(ctl[key], step_)
            ac.setValue(ctl[key], spin_value(key))
        ac.setPosition(ctl[key], x, y)
        ac.setVisible(ctl[key], 1)


def keep(fn):
    """AC stores callbacks without taking a reference: an unreferenced lambda gets freed and
    AC then calls freed memory (native crash in PythonForm::render). ui lives all session."""
    ui["callbacks"].append(fn)
    return fn


def build(ui_):
    """Create both windows. Runs once per session; callbacks are thin wrappers that look up
    the current module function, so they keep working after reloads. Settings controls are
    made and placed by sync_controls() on every init."""
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
    ac.setVisible(win, 0)
    ac.addRenderCallback(win, keep(lambda dt: g["render_settings"](dt)))
    # AC's own taskbar/close button can also show or hide it: keep our flag in sync
    ac.addOnAppActivatedListener(win, keep(lambda *a: ui_.update(settings_open=True)))
    ac.addOnAppDismissedListener(win, keep(lambda *a: ui_.update(settings_open=False)))


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
    apply_layout()  # widget first: a settings problem must not take the widget down
    ac.setSize(ui["settings"], SET_W, SET_H)  # here, not in build: layout changes on reload
    sync_controls()


def update(deltaT):
    global speed, vel, beta, rot_shown
    car = ac.getFocusedCar()
    speed = ac.getCarState(car, acsys.CS.SpeedKMH)
    slip[:] = ac.getCarState(car, acsys.CS.SlipRatio)
    shown[:] = step(speed, slip, deltaT)
    vel = ac.getCarState(car, acsys.CS.LocalVelocity)
    beta = body_slip(vel, speed)
    rot_shown = rot_step(beta, deltaT)
    if ui["settings_open"]:
        for key, text in live_text().items():
            ac.setText(ui["ctl"][key], text)


def live_text():
    """Text of the live labels in layout() (text None there)."""
    t = {"speed": "acsys.CS.SpeedKMH   {:.1f} km/h".format(speed),
         "vel": "acsys.CS.LocalVelocity   x {:+.2f}  z {:+.2f} m/s".format(vel[0], vel[2]),
         "beta": "beta  {:+.1f}".format(beta),
         "file": "settings.json  " + cfg_status[:70]}
    for i, (name, s) in enumerate(zip(WHEELS, slip)):
        t["wheel{}".format(i)] = "{}  {:+.3f}".format(name, s)
    return t

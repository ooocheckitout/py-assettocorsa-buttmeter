import importlib, json, os, sys, types


class Stub(types.ModuleType):
    """ac/acsys stand-in: every call is a no-op returning a fresh id."""
    n = 0

    def __getattr__(self, name):
        def call(*a, **k):
            Stub.n += 1
            return Stub.n
        return call


stub = sys.modules["ac"] = sys.modules["acsys"] = Stub("ac")
sys.modules["imp"] = importlib  # AC's Python 3.3 has imp; newer Pythons only importlib
stub.CS = types.SimpleNamespace(SpeedKMH=0, SlipRatio=1, LocalVelocity=2)
stub.GL = types.SimpleNamespace(Quads=0, Triangles=1)
car = {"speed": 100.0, "slip": [0.0] * 4, "vel": (0.0, 0.0, 27.0)}
stub.getCarState = lambda c, what: [car["speed"], list(car["slip"]), car["vel"]][what]
stub.getFocusedCar = lambda: 0
logs = []
stub.log = logs.append
values = {}
# AC keeps callbacks without a reference: record only weak refs, like AC, to catch freed ones
import gc, weakref
callbacks = []
for name in ("addRenderCallback", "addOnClickedListener", "addOnValueChangeListener",
             "addOnAppActivatedListener", "addOnAppDismissedListener"):
    setattr(stub, name, lambda ctrl, fn: callbacks.append(weakref.ref(fn)))
listeners = {}  # ctrl -> value-change listener; AC calls it from inside setValue/setRange


def on_value(ctrl, fn):
    callbacks.append(weakref.ref(fn))
    listeners[ctrl] = fn


def set_value(ctrl, v):
    values[ctrl] = v
    if ctrl in listeners:
        listeners[ctrl](v)


stub.addOnValueChangeListener = on_value
stub.setValue = set_value
stub.setRange = lambda ctrl, lo, hi: set_value(ctrl, max(lo, min(hi, values.get(ctrl, 0))))

sys.path.insert(0, "apps/python/WheelLock")
import wheellock_widget as w
w.SETTINGS_FILE = os.devnull + ".none"  # never touch the real settings.json
real_save = w.save_cfg
w.save_cfg = lambda: None
w.load_cfg()

# colour curve: exact stops at the thresholds (defaults lock/spin = 2, 10 %)
near = lambda c, d: all(abs(x - y) < 1e-9 for x, y in zip(c, d))
assert w.colour(0.0) == w.GREY and w.colour(-0.02) == w.GREY and w.colour(0.02) == w.GREY
assert near(w.colour(-0.10), w.PURPLE) and w.colour(-1.0) == w.PURPLE
assert near(w.colour(0.10), w.AMBER) and w.colour(3.0) == w.AMBER
assert near(w.colour(-0.06), w.lerp(w.GREY, w.PURPLE, 0.5))
assert near(w.colour(0.06), w.lerp(w.GREY, w.AMBER, 0.5))
print("curve ok")

# step: min speed, hold of a full event, hold expiry
assert w.step(5, [-1.0, 1.0, 0, 0], 0.016) == [w.GREY] * 4
out = w.step(100, [-0.2, 0.2, 0.0, 0.0], 0.016)
assert out[:2] == [w.PURPLE, w.AMBER] and out[2] == w.GREY
assert w.step(100, [0.0] * 4, 0.1)[:2] == [w.PURPLE, w.AMBER]  # held (120 ms)
assert w.step(100, [0.0] * 4, 0.05)[:2] == [w.GREY, w.GREY]    # expired
print("step ok")

# rotation: body slip angle sign (AC x = left), zones, red hold, low speed
assert abs(w.body_slip((-1.0, 0, 1.0), 100) - 45) < 1e-9   # travelling right of the nose
assert abs(w.body_slip((1.0, 0, 1.0), 100) + 45) < 1e-9
assert w.body_slip((5.0, 0, 0.1), 5) == 0.0                  # below min speed
assert [w.rot_colour(b) for b in (0, -2.9, 3, -3)] == [w.GREY] * 4    # <= start, like tyres
assert near(w.rot_colour(5.5), w.lerp(w.GREY, w.RED, 0.5)) and near(w.rot_colour(-5.5), w.rot_colour(5.5))
assert w.rot_colour(8) == w.RED and w.rot_colour(-120) == w.RED
assert w.rot_step(9, 0.016) == w.RED and w.rot_step(0, 0.1) == w.RED   # held
assert w.rot_step(0, 0.05) == w.GREY                                   # expired
print("rotation ok")

# thresholds stay strictly increasing whatever the user dials in
w.ui = {"ctl": {"lock.0": 101, "lock.1": 102}}
listeners[101] = lambda v: w.on_spin("lock.0", v)  # wired like AC: setValue re-enters
w.set_threshold("lock", 1, 1)        # full down to 1: start pushed below it
assert w.cfg["lock"] == [0, 1], w.cfg["lock"]
w.set_threshold("lock", 0, 150)      # start up to its max 99: full pushed up
assert w.cfg["lock"] == [99, 100], w.cfg["lock"]
assert values[101] == 99 and values[102] == 100
w.on_spin("lock.0", 3)                # a user edit still goes through
assert w.cfg["lock"] == [3, 100], w.cfg["lock"]
del listeners[101]
w.cfg["lock"] = [2, 10]

# safe area: tyres stay below the top bar, buttons stay clear of the CSP pin, at every scale
for k in w.SCALES:
    win_w, win_h, rects, btns, (cx, cy, reach) = w.geometry(k)
    assert reach <= cx <= win_w - reach and cy - reach >= w.BAR and cy + reach <= win_h, k  # lines fit at any angle
    assert all(y >= w.BAR and x >= 0 and x + rw <= win_w and y + rh <= win_h for x, y, rw, rh in rects), k
    assert all(x >= 0 and x + w.BTN <= win_w - w.PIN_W and y + w.BTN <= w.BAR for x, y in btns), k
print("layout ok")

# settings.json: every edit is written, a load reads it back, bad values reset per key
import tempfile
tmpdir = tempfile.mkdtemp()
w.SETTINGS_FILE, w.save_cfg = os.path.join(tmpdir, "settings.json"), real_save
w.ui = {"ctl": {}}
w.set_spinner = lambda key, v: None
w.load_cfg()
assert w.cfg_status == "no file yet, defaults" and w.cfg == w.DEFAULTS
w.on_spin("lock.0", 5)
w.on_spin("rotate.1", 12)
w.on_spin("hold_ms", 300)
assert w.cfg_status.startswith("saved ")
w.cfg.clear()
w.load_cfg()
assert w.cfg_status == "loaded", w.cfg_status
assert w.cfg["lock"] == [5, 10] and w.cfg["rotate"] == [3, 12] and w.cfg["hold_ms"] == 300, w.cfg
assert os.listdir(tmpdir) == ["settings.json"]  # temp file replaced, not left behind
with open(w.SETTINGS_FILE, "w") as f:
    json.dump({"lock": [9, 3], "spin": [4, 20], "scale": 7, "hold_ms": "x"}, f)
w.load_cfg()
assert w.cfg["spin"] == [4, 20] and w.cfg["lock"] == [2, 10] and w.cfg["scale"] == 1.0
assert w.cfg_status == "loaded, reset to default: hold_ms, lock, scale", w.cfg_status
with open(w.SETTINGS_FILE, "w") as f:
    f.write('{"lock": [5, ')  # half-written file
w.load_cfg()
assert w.cfg == w.DEFAULTS and w.cfg_status.startswith("unreadable")
del logs[:]
w.SETTINGS_FILE, w.save_cfg = os.devnull + ".none", lambda: None
del w.set_spinner  # back to the module function
w.load_cfg()
print("settings file ok")

# settings window: no two controls or GL drawings overlap, all inside the window.
# Text width per char measured from in-game screenshots (13 px font 6.8, 11 px 4.6).
CHAR_W = {13: 6.8, 11: 4.6}
w.speed, w.slip, w.vel, w.beta = 299.9, [-0.123] * 4, (-12.34, 0, 88.88), -45.6  # widest text
w.cfg_status = "NOT SAVED: [Errno 13] Permission denied: 'C:\\Program Files (x86)\\Steam\\x'"
live = w.live_text()
boxes = []
for key, spec in w.layout().items():
    if spec[0] == "label":
        _, text, x, y, size = spec
        text = live[key] if text is None else text
        boxes.append((key, x, y, len(text) * CHAR_W[size], size + 2))
    else:
        boxes.append((key, spec[1], spec[2], w.SPIN_W, w.SPIN_H))
gl_w = w.SWATCH_X + 20 - w.PLOT_X
boxes += [("slip curve", w.PLOT_X, w.CURVE_Y - 4, w.PLOT_W, w.CURVE_H + 8),
          ("wheel rows", w.PLOT_X, w.ROW_Y, gl_w, 4 * w.ROW_H),
          ("rot curve", w.PLOT_X, w.ROT_Y - 4, w.PLOT_W, w.CURVE_H + 8),
          ("beta row", w.PLOT_X, w.BETA_Y, gl_w, w.ROW_H)]
for k, x, y, bw, bh in boxes:
    assert 0 <= x and x + bw <= w.SET_W and 30 <= y and y + bh <= w.SET_H, (k, x, y, bw, bh)
for i, (k1, x1, y1, w1, h1) in enumerate(boxes):
    for k2, x2, y2, w2, h2 in boxes[i + 1:]:
        assert x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1, (k1, k2)
print("settings layout ok")

# full session: build, update, render both windows, toggle settings, hot reload keeps the ui
import WheelLock
WheelLock.widget.SETTINGS_FILE = w.SETTINGS_FILE
WheelLock.acMain(0)
ui = WheelLock.ui
# no settings file -> defaults; building the window (setRange/setValue fire listeners) must not edit them
assert WheelLock.widget.cfg == w.DEFAULTS, WheelLock.widget.cfg
spins = [k for k, spec in WheelLock.widget.layout().items() if spec[0] == "spin"]
assert all(values[ui["ctl"][k]] == WheelLock.widget.spin_value(k) for k in spins)
assert WheelLock.widget.geo is not None  # widget laid out
assert ui["app"] and ui["settings"] and len(ui["buttons"]) == 3
gc.collect()
assert len(callbacks) == 15 and all(r() for r in callbacks), [r() for r in callbacks]
callbacks[3]()(0.016)  # AC calling the widget render callback
WheelLock.widget.toggle_settings()
assert ui["settings_open"]
car["slip"] = [-0.07, 0.0, 0.0, 0.3]
car["vel"] = (-3.0, 0.0, 27.0)  # ~6 deg slide
WheelLock.acUpdate(0.016)
WheelLock.widget.render(0.016)
WheelLock.widget.render_settings(0.016)
before = dict(ui)
WheelLock.mtime = 0  # pretend the file changed
WheelLock.acUpdate(WheelLock.RELOAD_CHECK)
assert logs == ["WheelLock: reloaded"], logs
assert WheelLock.ui == before  # no duplicate windows or controls
assert near(WheelLock.widget.rot_shown, w.rot_colour(WheelLock.widget.beta)) and \
    WheelLock.widget.rot_shown != w.GREY
print("session ok")

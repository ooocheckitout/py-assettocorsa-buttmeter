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
stub.CS = types.SimpleNamespace(SpeedKMH=0, SlipRatio=1)
stub.GL = types.SimpleNamespace(Quads=0, Triangles=1)
car = {"speed": 100.0, "slip": [0.0] * 4}
stub.getCarState = lambda c, what: car["speed"] if what == 0 else list(car["slip"])
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
stub.setValue = lambda ctrl, v: values.__setitem__(ctrl, v)

sys.path.insert(0, "apps/python/WheelLock")
import wheellock_widget as w
w.SETTINGS_FILE = os.devnull + ".none"  # never touch the real settings.json
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

# thresholds stay strictly increasing whatever the user dials in
w.ui = {"lock": [101, 102], "spin": [103, 104]}
w.set_threshold("lock", 1, 1)        # full down to 1: start pushed below it
assert w.cfg["lock"] == [0, 1], w.cfg["lock"]
w.set_threshold("lock", 0, 150)      # start up to its max 99: full pushed up
assert w.cfg["lock"] == [99, 100], w.cfg["lock"]
assert values[101] == 99 and values[102] == 100
w.cfg["lock"] = [2, 10]

# safe area: tyres stay below the top bar, buttons stay clear of the CSP pin, at every scale
for k in w.SCALES:
    win_w, win_h, rects, btns = w.geometry(k)
    assert all(y >= w.BAR and x >= 0 and x + rw <= win_w and y + rh <= win_h for x, y, rw, rh in rects), k
    assert all(x >= 0 and x + w.BTN <= win_w - w.PIN_W and y + w.BTN <= w.BAR for x, y in btns), k
print("layout ok")

# full session: build, update, render both windows, toggle settings, hot reload keeps the ui
import WheelLock
WheelLock.widget.SETTINGS_FILE = w.SETTINGS_FILE
WheelLock.acMain(0)
ui = WheelLock.ui
assert ui["app"] and ui["settings"] and len(ui["buttons"]) == 3
gc.collect()
assert len(callbacks) == 13 and all(r() for r in callbacks), [r() for r in callbacks]
callbacks[3]()(0.016)  # AC calling the widget render callback
WheelLock.widget.toggle_settings()
assert ui["settings_open"]
car["slip"] = [-0.07, 0.0, 0.0, 0.3]
WheelLock.acUpdate(0.016)
WheelLock.widget.render(0.016)
WheelLock.widget.render_settings(0.016)
before = dict(ui)
WheelLock.mtime = 0  # pretend the file changed
WheelLock.acUpdate(WheelLock.RELOAD_CHECK)
assert logs == ["WheelLock: reloaded"], logs
assert WheelLock.ui == before  # no duplicate windows or controls
print("session ok")

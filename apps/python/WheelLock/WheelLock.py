# Entry point AC loads. Owns the ui dict (window and control ids), which lives for the whole
# session; all logic is in wheellock_widget.py, reloaded in place whenever that file changes.
# Changes to this file still need a new session.
import imp
import os
import sys
import traceback
import ac

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wheellock_widget as widget

RELOAD_CHECK = 1.0  # s between mtime checks

ui = {}  # filled once by widget.init; control ids and callbacks survive reloads
since_check = 0.0
mtime = os.path.getmtime(widget.__file__)


def log(msg):
    ac.log("WheelLock: " + msg)
    ac.console("WheelLock: " + msg.splitlines()[-1])


def reload_if_changed():
    global mtime
    now = os.path.getmtime(widget.__file__)
    if now == mtime:
        return
    mtime = now
    try:
        imp.reload(widget)
        widget.init(ui)
        log("reloaded")
    except Exception:
        log(traceback.format_exc())


def acMain(ac_version):
    widget.init(ui)
    return "WheelLock"


def acUpdate(deltaT):
    global since_check
    since_check += deltaT
    if since_check >= RELOAD_CHECK:
        since_check = 0.0
        reload_if_changed()
    widget.update(deltaT)

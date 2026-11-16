import os
import sys

import ac

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import AMBER, GREY, PURPLE, Bar, ColorRange, draw_gradient, draw_marker_row, draw_ticks
from settings import Settings, Threshold, load_settings, save_settings, with_threshold
from telemetry import WheelSlips, idle_wheel_slips, read_wheel_slips

APP_NAME = "widget"
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
BAR_LEFT = 10
BAR_TOP = 40
BAR_WIDTH = 270
BAR_HEIGHT = 20
ROW_HEIGHT = 12
SPINNER_TOP = 140

settings = load_settings(SETTINGS_PATH)
wheel_slips = idle_wheel_slips()
listeners = []


def lock_range(threshold: Threshold) -> ColorRange:
    return ColorRange(-threshold.start / 100, -threshold.full / 100, GREY, PURPLE)


def spin_range(threshold: Threshold) -> ColorRange:
    return ColorRange(threshold.start / 100, threshold.full / 100, GREY, AMBER)


def create_bar(settings: Settings) -> Bar:
    half = max(settings.lock.full, settings.spin.full) / 100 * 1.25
    return Bar(BAR_LEFT, BAR_TOP, BAR_WIDTH, BAR_HEIGHT, half)


def wheel_values(slips: WheelSlips) -> tuple:
    return (slips.front_left, slips.front_right, slips.rear_left, slips.rear_right)


def draw_widget(settings: Settings, slips: WheelSlips) -> None:
    bar = create_bar(settings)
    color_ranges = [lock_range(settings.lock), spin_range(settings.spin)]
    draw_gradient(bar, color_ranges)
    draw_ticks(bar, color_ranges)
    rows_top = BAR_TOP + BAR_HEIGHT + 10
    for row, slip in enumerate(wheel_values(slips)):
        draw_marker_row(bar, rows_top + row * ROW_HEIGHT, ROW_HEIGHT, slip)


def add_spinner(app_id: int, label: str, left: float, top: float, value: float,
                on_change: object) -> int:
    spinner = ac.addSpinner(app_id, label)
    ac.setPosition(spinner, left, top)
    ac.setSize(spinner, 100, 20)
    ac.setRange(spinner, 1, 50)
    ac.setStep(spinner, 1)
    ac.setValue(spinner, value)
    ac.addOnValueChangeListener(spinner, on_change)
    return spinner


def threshold_listener(kind: str, field: str) -> object:
    return lambda value: on_threshold(kind, field, value)


def create_threshold_spinners(app_id: int, settings: Settings) -> list:
    created = []
    for row, kind in enumerate(("lock", "spin")):
        for column, field in enumerate(("start", "full")):
            listener = threshold_listener(kind, field)
            created.append(listener)
            add_spinner(app_id, kind + " " + field, BAR_LEFT + column * 140,
                        SPINNER_TOP + row * 50, getattr(getattr(settings, kind), field), listener)
    return created


def on_threshold(kind: str, field: str, value: float) -> None:
    global settings
    settings = with_threshold(settings, kind, field, value)
    save_settings(settings, SETTINGS_PATH)


def render_widget(delta_time: float) -> None:
    draw_widget(settings, wheel_slips)


def acMain(ac_version: str) -> str:
    app_id = ac.newApp(APP_NAME)
    ac.setSize(app_id, BAR_LEFT * 2 + BAR_WIDTH, SPINNER_TOP + 90)
    listeners.extend(create_threshold_spinners(app_id, settings))
    ac.addRenderCallback(app_id, render_widget)
    return APP_NAME


def acUpdate(delta_time: float) -> None:
    global wheel_slips
    wheel_slips = read_wheel_slips()

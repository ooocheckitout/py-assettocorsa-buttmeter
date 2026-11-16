import os
import sys

import ac

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import (
    AMBER,
    GREY,
    PURPLE,
    Bar,
    ColorRange,
    draw_gradient,
    draw_marker_row,
    draw_ticks,
)
from settings import Settings, Threshold, load_settings, save_settings
from telemetry import WheelSlips, idle_wheel_slips, read_wheel_slips

APP_NAME = "widget"
SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "settings.json"
)
BAR_LEFT = 10
BAR_TOP = 40
BAR_WIDTH = 270
BAR_HEIGHT = 20
ROW_HEIGHT = 12
ROWS_TOP = BAR_TOP + BAR_HEIGHT + 10
LABEL_WIDTH = 50
SPINNER_TOP = 140

settings = load_settings(SETTINGS_PATH)
wheel_slips = idle_wheel_slips()
listeners = []
value_labels = []


def lock_range(threshold: Threshold) -> ColorRange:
    return ColorRange(-threshold.start / 100, -threshold.end / 100, GREY, PURPLE)


def spin_range(threshold: Threshold) -> ColorRange:
    return ColorRange(threshold.start / 100, threshold.end / 100, GREY, AMBER)


def create_bar(settings: Settings) -> Bar:
    half = max(settings.lock.end, settings.spin.end) / 100 * 1.25
    return Bar(BAR_LEFT, BAR_TOP, BAR_WIDTH, BAR_HEIGHT, half)


def wheel_values(slips: WheelSlips) -> tuple:
    return (slips.front_left, slips.front_right, slips.rear_left, slips.rear_right)


def slip_text(slip: float) -> str:
    return "{:+.1f}%".format(slip * 100)


def draw_widget(settings: Settings, slips: WheelSlips) -> None:
    bar = create_bar(settings)
    color_ranges = [lock_range(settings.lock), spin_range(settings.spin)]
    draw_gradient(bar, color_ranges)
    draw_ticks(bar, color_ranges)
    for row, slip in enumerate(wheel_values(slips)):
        draw_marker_row(bar, ROWS_TOP + row * ROW_HEIGHT, ROW_HEIGHT, slip)


def update_value_labels(labels: list, slips: WheelSlips) -> None:
    for label, slip in zip(labels, wheel_values(slips)):
        ac.setText(label, slip_text(slip))


def add_value_label(app_id: int, top: float) -> int:
    label = ac.addLabel(app_id, slip_text(0.0))
    ac.setPosition(label, BAR_LEFT + BAR_WIDTH + 4, top - 2)
    ac.setSize(label, LABEL_WIDTH, ROW_HEIGHT)
    ac.setFontSize(label, 10)
    ac.setFontAlignment(label, "right")
    return label


def add_spinner(
    app_id: int, label: str, left: float, top: float, value: float, on_change: object
) -> int:
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


def on_threshold(kind: str, field: str, value: float) -> None:
    setattr(getattr(settings, kind), field, value)
    save_settings(settings, SETTINGS_PATH)


def render_widget(delta_time: float) -> None:
    draw_widget(settings, wheel_slips)


def acMain(ac_version: str) -> str:
    app_id = ac.newApp(APP_NAME)
    ac.setSize(app_id, BAR_LEFT * 2 + BAR_WIDTH + LABEL_WIDTH, SPINNER_TOP + 90)
    for row in range(4):
        value_labels.append(add_value_label(app_id, ROWS_TOP + row * ROW_HEIGHT))
    for row, kind in enumerate(("lock", "spin")):
        for column, field in enumerate(("start", "end")):
            listener = threshold_listener(kind, field)
            listeners.append(listener)
            add_spinner(
                app_id,
                kind + " " + field,
                BAR_LEFT + column * 140,
                SPINNER_TOP + row * 50,
                getattr(getattr(settings, kind), field),
                listener,
            )
    ac.addRenderCallback(app_id, render_widget)
    return APP_NAME


def acUpdate(delta_time: float) -> None:
    global wheel_slips
    wheel_slips = read_wheel_slips()
    update_value_labels(value_labels, wheel_slips)

import os
import sys
import traceback

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
MARGIN = 10
LABEL_WIDTH = 75
BAR_LEFT = MARGIN + LABEL_WIDTH
BAR_TOP = 40
BAR_WIDTH = 270
BAR_HEIGHT = 20
ROW_HEIGHT = 16
ROWS_TOP = BAR_TOP + BAR_HEIGHT + 10
SPINNER_TOP = 160
STEPPER_WIDTH = 100
BUTTON_SIZE = 20
STEP = 0.01
THRESHOLD_MIN = 0.01
THRESHOLD_MAX = 0.5
WHEEL_NAMES = ("FL", "FR", "RL", "RR")

settings = load_settings(SETTINGS_PATH)
wheel_slips = idle_wheel_slips()
listeners = []
value_labels = []


def lock_range(threshold: Threshold) -> ColorRange:
    return ColorRange(-threshold.start, -threshold.end, GREY, PURPLE)


def spin_range(threshold: Threshold) -> ColorRange:
    return ColorRange(threshold.start, threshold.end, GREY, AMBER)


def create_bar(settings: Settings) -> Bar:
    half = max(settings.lock.end, settings.spin.end) * 1.25
    return Bar(BAR_LEFT, BAR_TOP, BAR_WIDTH, BAR_HEIGHT, half)


def wheel_values(slips: WheelSlips) -> tuple:
    return (slips.front_left, slips.front_right, slips.rear_left, slips.rear_right)


def slip_text(wheel: str, slip: float) -> str:
    return "{} {:.2f}".format(wheel, slip)


def draw_widget(settings: Settings, slips: WheelSlips) -> None:
    bar = create_bar(settings)
    color_ranges = [lock_range(settings.lock), spin_range(settings.spin)]
    draw_gradient(bar, color_ranges)
    draw_ticks(bar, color_ranges)
    for row, slip in enumerate(wheel_values(slips)):
        draw_marker_row(bar, ROWS_TOP + row * ROW_HEIGHT, ROW_HEIGHT, slip)


def update_value_labels(labels: list, slips: WheelSlips) -> None:
    for label, wheel, slip in zip(labels, WHEEL_NAMES, wheel_values(slips)):
        ac.setText(label, slip_text(wheel, slip))


def add_label(app_id: int, text: str, top: float) -> int:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, MARGIN, top - 1)
    ac.setSize(label, LABEL_WIDTH, ROW_HEIGHT)
    ac.setFontSize(label, 14)
    ac.setFontAlignment(label, "left")
    return label


def threshold_text(value: float) -> str:
    return "{:.2f}".format(value)


def stepped(value: float, delta: float) -> float:
    return round(min(THRESHOLD_MAX, max(THRESHOLD_MIN, value + delta)), 2)


def add_text(
    app_id: int, text: str, left: float, top: float, width: float, size: float
) -> int:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, left, top)
    ac.setSize(label, width, 20)
    ac.setFontSize(label, size)
    ac.setFontAlignment(label, "center")
    return label


def add_button(
    app_id: int, text: str, left: float, top: float, on_click: object
) -> int:
    button = ac.addButton(app_id, text)
    ac.setPosition(button, left, top)
    ac.setSize(button, BUTTON_SIZE, BUTTON_SIZE)
    ac.addOnClickedListener(button, on_click)
    return button


def add_stepper(app_id: int, kind: str, field: str, left: float, top: float) -> None:
    add_text(app_id, field, left, top - 18, STEPPER_WIDTH, 12)
    value = getattr(getattr(settings, kind), field)
    value_label = add_text(
        app_id,
        threshold_text(value),
        left + BUTTON_SIZE,
        top,
        STEPPER_WIDTH - 2 * BUTTON_SIZE,
        14,
    )
    for text, delta, offset in (
        ("-", -STEP, 0),
        ("+", STEP, STEPPER_WIDTH - BUTTON_SIZE),
    ):
        listener = threshold_listener(kind, field, delta, value_label)
        listeners.append(listener)
        add_button(app_id, text, left + offset, top, listener)


def threshold_listener(kind: str, field: str, delta: float, label: int) -> object:
    return lambda x, y: on_threshold(kind, field, delta, label)


def on_threshold(kind: str, field: str, delta: float, label: int) -> None:
    threshold = getattr(settings, kind)
    value = stepped(getattr(threshold, field), delta)
    setattr(threshold, field, value)
    ac.setText(label, threshold_text(value))
    save_settings(settings, SETTINGS_PATH)


def render_widget(delta_time: float) -> None:
    draw_widget(settings, wheel_slips)


def acMain(ac_version: str) -> str:
    try:
        return create_app()
    except Exception:
        ac.log("widget acMain failed: " + traceback.format_exc())
        raise


def create_app() -> str:
    app_id = ac.newApp(APP_NAME)
    ac.setSize(app_id, BAR_LEFT + BAR_WIDTH + MARGIN, SPINNER_TOP + 90)
    add_label(app_id, "Slip ratio", BAR_TOP + 2)
    for row, wheel in enumerate(WHEEL_NAMES):
        value_labels.append(
            add_label(app_id, slip_text(wheel, 0.0), ROWS_TOP + row * ROW_HEIGHT)
        )
    for row, kind in enumerate(("lock", "spin")):
        add_label(app_id, kind.capitalize(), SPINNER_TOP + row * 50 + 2)
        for column, field in enumerate(("start", "end")):
            add_stepper(
                app_id,
                kind,
                field,
                BAR_LEFT + column * (BAR_WIDTH - STEPPER_WIDTH),
                SPINNER_TOP + row * 50,
            )
    ac.addRenderCallback(app_id, render_widget)
    return APP_NAME


def acUpdate(delta_time: float) -> None:
    global wheel_slips
    wheel_slips = read_wheel_slips()
    update_value_labels(value_labels, wheel_slips)

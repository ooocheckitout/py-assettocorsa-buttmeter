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
from telemetry import Telemetry, WheelSlips, idle_telemetry, read_telemetry

APP_NAME = "widget"
SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "settings.json"
)
MARGIN = 10
LABEL_WIDTH = 75
BAR_LEFT = MARGIN + LABEL_WIDTH
FIRST_TOP = 40
BAR_WIDTH = 270
BAR_HEIGHT = 20
ROW_HEIGHT = 16
ROWS_GAP = 10
STEPPERS_GAP = 26
ZONE_HEIGHT = 50
STEPPER_WIDTH = 100
BUTTON_SIZE = 20
WHEEL_NAMES = ("FL", "FR", "RL", "RR")


class Zone:
    def __init__(self, kind: str, title: str, sides: tuple, color: tuple) -> None:
        self.kind = kind
        self.title = title
        self.sides = sides
        self.color = color


class Gauge:
    def __init__(
        self,
        title: str,
        zones: list,
        row_names: tuple,
        read: object,
        step: float,
        minimum: float,
        maximum: float,
        digits: int,
    ) -> None:
        self.title = title
        self.zones = zones
        self.row_names = row_names
        self.read = read
        self.step = step
        self.minimum = minimum
        self.maximum = maximum
        self.digits = digits


def wheel_values(slips: WheelSlips) -> tuple:
    return (slips.front_left, slips.front_right, slips.rear_left, slips.rear_right)


GAUGES = (
    Gauge(
        "Slip ratio",
        [Zone("lock", "Lock", (-1,), PURPLE), Zone("spin", "Spin", (1,), AMBER)],
        WHEEL_NAMES,
        lambda telemetry: wheel_values(telemetry.slip_ratios),
        0.01,
        0.01,
        0.5,
        2,
    ),
    Gauge(
        "Slip angle",
        [Zone("slip_angle", "Limit", (-1, 1), AMBER)],
        WHEEL_NAMES,
        lambda telemetry: wheel_values(telemetry.slip_angles),
        0.5,
        0.5,
        30.0,
        1,
    ),
    Gauge(
        "Yaw rate",
        [Zone("yaw_rate", "Limit", (-1, 1), AMBER)],
        ("",),
        lambda telemetry: (telemetry.yaw_rate,),
        1.0,
        1.0,
        180.0,
        1,
    ),
)

settings = load_settings(SETTINGS_PATH)
telemetry = idle_telemetry()
listeners = []
value_labels = []


def gauge_height(gauge: Gauge) -> float:
    return (
        BAR_HEIGHT
        + ROWS_GAP
        + len(gauge.row_names) * ROW_HEIGHT
        + STEPPERS_GAP
        + len(gauge.zones) * ZONE_HEIGHT
    )


def gauge_tops(gauges: tuple) -> list:
    tops = [FIRST_TOP]
    for gauge in gauges:
        tops.append(tops[-1] + gauge_height(gauge))
    return tops


def rows_top(top: float) -> float:
    return top + BAR_HEIGHT + ROWS_GAP


def steppers_top(gauge: Gauge, top: float) -> float:
    return rows_top(top) + len(gauge.row_names) * ROW_HEIGHT + STEPPERS_GAP


def zone_ranges(zone: Zone, threshold: Threshold) -> list:
    return [
        ColorRange(side * threshold.start, side * threshold.end, GREY, zone.color)
        for side in zone.sides
    ]


def color_ranges(gauge: Gauge, settings: Settings) -> list:
    return [
        color_range
        for zone in gauge.zones
        for color_range in zone_ranges(zone, getattr(settings, zone.kind))
    ]


def create_bar(gauge: Gauge, settings: Settings, top: float) -> Bar:
    half = max(getattr(settings, zone.kind).end for zone in gauge.zones) * 1.25
    return Bar(BAR_LEFT, top, BAR_WIDTH, BAR_HEIGHT, half)


def number_text(value: float, digits: int) -> str:
    return "{:.{}f}".format(value, digits)


def value_text(name: str, value: float, digits: int) -> str:
    return "{} {}".format(name, number_text(value, digits)).strip()


def draw_gauge(gauge: Gauge, settings: Settings, values: tuple, top: float) -> None:
    bar = create_bar(gauge, settings, top)
    ranges = color_ranges(gauge, settings)
    draw_gradient(bar, ranges)
    draw_ticks(bar, ranges)
    for row, value in enumerate(values):
        draw_marker_row(bar, rows_top(top) + row * ROW_HEIGHT, ROW_HEIGHT, value)


def update_value_labels(
    labels: list, gauge: Gauge, values: tuple
) -> None:
    for label, name, value in zip(labels, gauge.row_names, values):
        ac.setText(label, value_text(name, value, gauge.digits))


def add_label(app_id: int, text: str, top: float) -> int:
    label = ac.addLabel(app_id, text)
    ac.setPosition(label, MARGIN, top - 1)
    ac.setSize(label, LABEL_WIDTH, ROW_HEIGHT)
    ac.setFontSize(label, 14)
    ac.setFontAlignment(label, "left")
    return label


def stepped(value: float, delta: float, gauge: Gauge) -> float:
    return round(min(gauge.maximum, max(gauge.minimum, value + delta)), gauge.digits)


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


def add_stepper(
    app_id: int, gauge: Gauge, kind: str, field: str, left: float, top: float
) -> None:
    add_text(app_id, field, left, top - 18, STEPPER_WIDTH, 12)
    value = getattr(getattr(settings, kind), field)
    value_label = add_text(
        app_id,
        number_text(value, gauge.digits),
        left + BUTTON_SIZE,
        top,
        STEPPER_WIDTH - 2 * BUTTON_SIZE,
        14,
    )
    for text, delta, offset in (
        ("-", -gauge.step, 0),
        ("+", gauge.step, STEPPER_WIDTH - BUTTON_SIZE),
    ):
        listener = threshold_listener(gauge, kind, field, delta, value_label)
        listeners.append(listener)
        add_button(app_id, text, left + offset, top, listener)


def threshold_listener(
    gauge: Gauge, kind: str, field: str, delta: float, label: int
) -> object:
    return lambda x, y: on_threshold(gauge, kind, field, delta, label)


def on_threshold(gauge: Gauge, kind: str, field: str, delta: float, label: int) -> None:
    threshold = getattr(settings, kind)
    value = stepped(getattr(threshold, field), delta, gauge)
    setattr(threshold, field, value)
    ac.setText(label, number_text(value, gauge.digits))
    save_settings(settings, SETTINGS_PATH)


def add_gauge(app_id: int, gauge: Gauge, top: float) -> list:
    add_label(app_id, gauge.title, top + 2)
    for row, zone in enumerate(gauge.zones):
        zone_top = steppers_top(gauge, top) + row * ZONE_HEIGHT
        add_label(app_id, zone.title, zone_top + 2)
        for column, field in enumerate(("start", "end")):
            add_stepper(
                app_id,
                gauge,
                zone.kind,
                field,
                BAR_LEFT + column * (BAR_WIDTH - STEPPER_WIDTH),
                zone_top,
            )
    return [
        add_label(
            app_id,
            value_text(name, 0.0, gauge.digits),
            rows_top(top) + row * ROW_HEIGHT,
        )
        for row, name in enumerate(gauge.row_names)
    ]


def render_widget(delta_time: float) -> None:
    for gauge, top in zip(GAUGES, gauge_tops(GAUGES)):
        draw_gauge(gauge, settings, gauge.read(telemetry), top)


def acMain(ac_version: str) -> str:
    try:
        return create_app()
    except Exception:
        ac.log("widget acMain failed: " + traceback.format_exc())
        raise


def create_app() -> str:
    app_id = ac.newApp(APP_NAME)
    tops = gauge_tops(GAUGES)
    ac.setSize(app_id, BAR_LEFT + BAR_WIDTH + MARGIN, tops[-1] - MARGIN)
    for gauge, top in zip(GAUGES, tops):
        value_labels.append(add_gauge(app_id, gauge, top))
    ac.addRenderCallback(app_id, render_widget)
    return APP_NAME


def acUpdate(delta_time: float) -> None:
    global telemetry
    telemetry = read_telemetry()
    for labels, gauge in zip(value_labels, GAUGES):
        update_value_labels(labels, gauge, gauge.read(telemetry))

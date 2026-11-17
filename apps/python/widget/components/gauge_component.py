import ac

from render import Color, Component, Slot
from settings import Settings, Threshold, save_settings
from telemetry import Snapshot


class Gauge:
    def __init__(
        self,
        title: str,
        names: tuple,
        read: object,
        step: float,
        digits: int,
        negative: Threshold,
        positive: Threshold,
        negative_color: Color,
        positive_color: Color,
        negative_title: str,
        positive_title: str,
    ) -> None:
        self.title = title
        self.names = names
        self.read = read
        self.step = step
        self.digits = digits
        self.negative = negative
        self.positive = positive
        self.negative_color = negative_color
        self.positive_color = positive_color
        self.negative_title = negative_title
        self.positive_title = positive_title

    def steppers(self) -> list:
        if self.negative is self.positive:
            return [(self.positive_title, self.positive)]
        return [
            (self.negative_title, self.negative),
            (self.positive_title, self.positive),
        ]

    def color(self, value: float) -> Color:
        if value < 0:
            return Component.shade(self.negative, self.negative_color, value)
        return Component.shade(self.positive, self.positive_color, value)

    def number(self, value: float) -> str:
        return "{:.{}f}".format(value, self.digits)


class GaugeComponent(Component):
    label_width = 75
    bar_height = 20
    row_height = 16
    rows_gap = 10
    steppers_gap = 26
    limit_height = 50
    stepper_width = 100
    button_size = 20

    def __init__(
        self, app_id: int, area: Slot, gauge: Gauge, settings: Settings
    ) -> None:
        self.gauge = gauge
        self.settings = settings
        self.listeners = []
        bar_left = area.left + self.label_width
        bar_width = area.width - self.label_width
        self.bar = Slot(bar_left, area.top, bar_width, self.bar_height)

        rows_top = area.top + self.bar_height + self.rows_gap
        self.rows = [
            Slot(bar_left, rows_top + row * self.row_height, bar_width, self.row_height)
            for row in range(len(gauge.names))
        ]

        self.label(
            app_id, gauge.title, self.caption(area.left, area.top + 1), 14, "left"
        )
        self.values = [
            self.label(app_id, name, self.caption(area.left, row.top - 1), 14, "left")
            for name, row in zip(gauge.names, self.rows)
        ]

        steppers_top = rows_top + len(self.rows) * self.row_height + self.steppers_gap
        for index, (title, threshold) in enumerate(gauge.steppers()):
            limit_top = steppers_top + index * self.limit_height
            self.label(app_id, title, self.caption(area.left, limit_top + 1), 14, "left")
            for column, field in enumerate(("start", "end")):
                stepper_left = bar_left + column * (bar_width - self.stepper_width)
                self.add_stepper(
                    app_id,
                    threshold,
                    field,
                    Slot(stepper_left, limit_top, self.stepper_width, self.button_size),
                )

        self.height = steppers_top + len(gauge.steppers()) * self.limit_height - area.top

    def caption(self, left: float, top: float) -> Slot:
        return Slot(left, top, self.label_width, self.row_height)

    def add_stepper(
        self, app_id: int, threshold: Threshold, field: str, slot: Slot
    ) -> None:
        self.label(
            app_id, field, Slot(slot.left, slot.top - 18, slot.width, 20), 12, "center"
        )
        value_label = self.label(
            app_id,
            self.gauge.number(getattr(threshold, field)),
            Slot(
                slot.left + self.button_size,
                slot.top,
                slot.width - 2 * self.button_size,
                slot.height,
            ),
            14,
            "center",
        )
        for text, sign, offset in (
            ("-", -1, 0),
            ("+", 1, slot.width - self.button_size),
        ):
            listener = self.stepper_listener(
                threshold, field, sign * self.gauge.step, value_label
            )
            self.listeners.append(listener)
            self.button(
                app_id,
                text,
                Slot(slot.left + offset, slot.top, self.button_size, self.button_size),
                listener,
            )

    def stepper_listener(
        self,
        threshold: Threshold,
        field: str,
        delta: float,
        value_label: int,
    ) -> object:
        return lambda x, y: self.step(threshold, field, delta, value_label)

    def step(
        self,
        threshold: Threshold,
        field: str,
        delta: float,
        value_label: int,
    ) -> None:
        step = self.gauge.step
        if field == "start":
            value = min(threshold.end - step, max(step, threshold.start + delta))
        else:
            value = max(threshold.start + step, threshold.end + delta)
        value = round(value, self.gauge.digits)
        setattr(threshold, field, value)
        ac.setText(value_label, self.gauge.number(value))
        save_settings(self.settings)

    def pixel(self, value: float, half: float) -> float:
        clamped = max(-half, min(half, value))
        return self.bar.left + (clamped + half) / (2 * half) * self.bar.width

    def update(self, snapshot: Snapshot) -> None:
        half = max(self.gauge.negative.end, self.gauge.positive.end) * 1.25

        for column in range(int(self.bar.width)):
            value = (column + 0.5) / self.bar.width * 2 * half - half
            self.fill(
                Slot(self.bar.left + column, self.bar.top, 1, self.bar.height),
                self.gauge.color(value),
            )

        ticks = [
            0.0,
            -self.gauge.negative.start,
            -self.gauge.negative.end,
            self.gauge.positive.start,
            self.gauge.positive.end,
        ]
        for tick in ticks:
            self.fill(
                Slot(
                    self.pixel(tick, half) - 0.5,
                    self.bar.top - 4,
                    1,
                    self.bar.height + 8,
                ),
                Color.white,
            )

        values = self.gauge.read(snapshot)
        for row, value_label, name, value in zip(
            self.rows, self.values, self.gauge.names, values
        ):
            middle = row.top + row.height / 2
            self.fill(Slot(row.left, middle - 1, row.width, 2), Color.faint)
            self.fill(
                Slot(self.pixel(value, half) - 2, row.top + 2, 4, row.height - 4),
                Color.white,
            )
            ac.setText(
                value_label, "{} {}".format(name, self.gauge.number(value)).strip()
            )

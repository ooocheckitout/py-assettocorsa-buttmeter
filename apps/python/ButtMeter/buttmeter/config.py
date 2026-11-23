import json
import os

from buttmeter.render import Color, KnownColors


class Threshold:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end

    def level(self, value: float) -> float:
        if self.end <= self.start:
            return 1.0 if abs(value) >= self.start else 0.0
        level = (abs(value) - self.start) / (self.end - self.start)
        return max(0.0, min(level, 1.0))


def threshold_fill(value: float, threshold: Threshold, color: Color) -> Color:
    return KnownColors.grey.mix(color, threshold.level(value))


def slip_ratio_fill(slip_ratio: float, lock: Threshold, spin: Threshold) -> Color:
    if slip_ratio < 0:
        return threshold_fill(slip_ratio, lock, KnownColors.purple)
    return threshold_fill(slip_ratio, spin, KnownColors.amber)


class Settings:
    def __init__(
        self,
        lock: Threshold,
        spin: Threshold,
        understeer: Threshold,
        oversteer: Threshold,
        body_slip: Threshold,
        scale: float,
    ) -> None:
        self.lock = lock
        self.spin = spin
        self.understeer = understeer
        self.oversteer = oversteer
        self.body_slip = body_slip
        self.scale = scale

    @staticmethod
    def from_dict(saved: dict) -> "Settings":
        return Settings(
            lock=Threshold(**saved["lock"]),
            spin=Threshold(**saved["spin"]),
            understeer=Threshold(**saved["understeer"]),
            oversteer=Threshold(**saved["oversteer"]),
            body_slip=Threshold(**saved["body_slip"]),
            scale=saved["scale"],
        )

    def to_dict(self) -> dict:
        return {
            "lock": vars(self.lock),
            "spin": vars(self.spin),
            "understeer": vars(self.understeer),
            "oversteer": vars(self.oversteer),
            "body_slip": vars(self.body_slip),
            "scale": self.scale,
        }


def default_settings() -> Settings:
    return Settings(
        lock=Threshold(0.05, 0.1),
        spin=Threshold(0.07, 0.1),
        understeer=Threshold(6.0, 8.0),
        oversteer=Threshold(6.0, 8.0),
        body_slip=Threshold(3.0, 6.0),
        scale=1.0,
    )


app_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(app_directory, "settings.json")


def load_settings() -> Settings:
    try:
        with open(path) as file:
            return Settings.from_dict(json.load(file))
    except (OSError, ValueError, TypeError, KeyError):
        settings = default_settings()
        save_settings(settings)
        return settings


def save_settings(settings: Settings) -> None:
    with open(path, "w") as file:
        json.dump(settings.to_dict(), file, indent=2, sort_keys=True)

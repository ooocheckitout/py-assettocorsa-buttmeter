import json
import os


class Threshold:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end

    def level(self, value: float) -> float:
        level = (abs(value) - self.start) / (self.end - self.start)
        return max(0.0, min(level, 1.0))


class Settings:
    def __init__(
        self,
        lock: Threshold,
        spin: Threshold,
        slip_angle: Threshold,
        yaw_rate: Threshold,
    ) -> None:
        self.lock = lock
        self.spin = spin
        self.slip_angle = slip_angle
        self.yaw_rate = yaw_rate


path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load_settings() -> Settings:
    with open(path) as file:
        saved = json.load(file)
    return Settings(**{name: Threshold(**values) for name, values in saved.items()})


def save_settings(settings: Settings) -> None:
    with open(path, "w") as file:
        json.dump(settings, file, default=vars, indent=2, sort_keys=True)

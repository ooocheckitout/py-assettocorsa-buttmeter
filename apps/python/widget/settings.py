import json


class Threshold:
    def __init__(self, start: float, end: float) -> None:
        self.start = float(start)
        self.end = float(end)


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


def default_settings() -> Settings:
    return Settings(
        Threshold(0.05, 0.1),
        Threshold(0.05, 0.1),
        Threshold(6.0, 8.0),
        Threshold(0.2, 0.6),
    )


def load_settings(path: str) -> Settings:
    try:
        with open(path) as file:
            raw = json.load(file)
        thresholds = vars(default_settings())
        thresholds.update(
            {kind: Threshold(**values) for kind, values in raw.items()}
        )
        return Settings(**thresholds)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return default_settings()


def save_settings(settings: Settings, path: str) -> None:
    with open(path, "w") as file:
        json.dump(settings, file, default=vars, indent=2)

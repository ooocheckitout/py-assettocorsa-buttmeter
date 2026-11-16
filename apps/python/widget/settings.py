import json


class Threshold:
    def __init__(self, start: float, end: float) -> None:
        self.start = float(start)
        self.end = float(end)


class Settings:
    def __init__(self, lock: Threshold, spin: Threshold) -> None:
        self.lock = lock
        self.spin = spin


def default_settings() -> Settings:
    return Settings(Threshold(0.05, 0.1), Threshold(0.05, 0.1))


def load_settings(path: str) -> Settings:
    try:
        with open(path) as file:
            raw = json.load(file)
        return Settings(**{kind: Threshold(**values) for kind, values in raw.items()})
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return default_settings()


def save_settings(settings: Settings, path: str) -> None:
    with open(path, "w") as file:
        json.dump(settings, file, default=vars, indent=2)

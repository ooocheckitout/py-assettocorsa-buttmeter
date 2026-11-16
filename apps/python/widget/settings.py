import json


class Threshold:
    def __init__(self, start: float, full: float) -> None:
        self.start = start
        self.full = full


class Settings:
    def __init__(self, lock: Threshold, spin: Threshold) -> None:
        self.lock = lock
        self.spin = spin


def default_settings() -> Settings:
    return Settings(Threshold(5.0, 10.0), Threshold(5.0, 10.0))


def read_threshold(raw: dict) -> Threshold:
    return Threshold(float(raw["start"]), float(raw["full"]))


def load_settings(path: str) -> Settings:
    try:
        with open(path) as file:
            raw = json.load(file)
        return Settings(read_threshold(raw["lock"]), read_threshold(raw["spin"]))
    except (OSError, ValueError, KeyError, TypeError):
        return default_settings()


def save_settings(settings: Settings, path: str) -> None:
    thresholds = {"lock": vars(settings.lock), "spin": vars(settings.spin)}
    with open(path, "w") as file:
        json.dump(thresholds, file, indent=2)


def with_value(threshold: Threshold, field: str, value: float) -> Threshold:
    values = vars(threshold).copy()
    values[field] = value
    return Threshold(**values)


def with_threshold(settings: Settings, kind: str, field: str, value: float) -> Settings:
    thresholds = vars(settings).copy()
    thresholds[kind] = with_value(thresholds[kind], field, value)
    return Settings(**thresholds)

import json
import os


class Threshold:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end


class Settings:
    def __init__(
        self,
        lock: Threshold,
        spin: Threshold,
        understeer: Threshold,
        oversteer: Threshold,
        yaw_rate: Threshold,
        scale: float,
    ) -> None:
        self.lock = lock
        self.spin = spin
        self.understeer = understeer
        self.oversteer = oversteer
        self.yaw_rate = yaw_rate
        self.scale = scale

    @staticmethod
    def from_dict(saved: dict) -> "Settings":
        return Settings(
            lock=Threshold(**saved["lock"]),
            spin=Threshold(**saved["spin"]),
            understeer=Threshold(**saved["understeer"]),
            oversteer=Threshold(**saved["oversteer"]),
            yaw_rate=Threshold(**saved["yaw_rate"]),
            scale=saved["scale"],
        )

    def to_dict(self) -> dict:
        return {
            "lock": vars(self.lock),
            "spin": vars(self.spin),
            "understeer": vars(self.understeer),
            "oversteer": vars(self.oversteer),
            "yaw_rate": vars(self.yaw_rate),
            "scale": self.scale,
        }


def default_settings() -> Settings:
    return Settings(
        lock=Threshold(0.05, 0.1),
        spin=Threshold(0.05, 0.1),
        understeer=Threshold(6.0, 8.0),
        oversteer=Threshold(6.0, 8.0),
        yaw_rate=Threshold(0.2, 0.6),
        scale=1.0,
    )


path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


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

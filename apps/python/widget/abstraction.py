class ACWidget:
    def __init__(self, name: str) -> None:
        self.name = name

    def acMain(self, ac_version: str) -> str:
        """Runs once the session is loaded."""
        return self.name

    def acUpdate(self, delta_time_sec: float):
        """Runs every frame for the whole session."""

    def acShutdown(self):
        """Runs once when the session ends normally."""

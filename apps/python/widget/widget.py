import ac


def acMain(ac_version: str) -> str:
    """Runs once the session is loaded."""
    app = ac.newApp("WheelLock")
    return "WheelLock"


def acUpdate(deltaT: float) -> None:
    """Runs every frame for the whole session."""
    pass


def acShutdown() -> None:
    """Runs once when the session ends normally."""
    pass

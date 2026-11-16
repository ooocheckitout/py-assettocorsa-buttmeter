import ac
import acsys


def speed():
    """Car speed in km/h."""
    return ac.getCarState(0, acsys.CS.SpeedKMH)


def slipRatioPerWheel() -> list[float]:
    """Tire ratio between how fast it spins compared to the road speed."""
    return [x for x in ac.getCarState(0, acsys.CS.SlipRatio)]


def slipAnglePerWheel() -> list[float]:
    """Tire angle between where it points and where it travels in deg."""
    return [x for x in ac.getCarState(0, acsys.CS.SlipAngle)]


def velocityPerDim():
    """Car velocity in m/s"""
    return [x for x in ac.getCarState(0, acsys.CS.LocalVelocity)]


def yawRatePerDim():
    """Car rotation rate in rad/s"""
    return ac.getCarState(0, acsys.CS.LocalAngularVelocity)


def acMain(ac_version: str) -> str:
    """Runs once the session is loaded."""
    app_name = "widget"
    app_id = ac.newApp(app_name)
    ac.setSize(app_id, 400, 400)
    return app_name


def acUpdate(deltaT: float) -> None:
    """Runs every frame for the whole session."""
    pass


def acShutdown() -> None:
    """Runs once when the session ends normally."""
    pass

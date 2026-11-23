import math

import ac, acsys


class Wheel:
    def __init__(self, slip_ratio: float, slip_angle: float) -> None:
        self.slip_ratio = slip_ratio
        self.slip_angle = slip_angle


def body_slip(velocity: list) -> float:
    lateral, _, forward = velocity
    if math.hypot(lateral, forward) < 2.0:
        return 0.0
    return math.degrees(math.atan2(lateral, abs(forward)))


class Snapshot:
    def __init__(self, wheels: list, body_slip: float) -> None:
        self.wheels = wheels
        self.body_slip = body_slip


def read_snapshot() -> Snapshot:
    car = ac.getFocusedCar()
    ratios = ac.getCarState(car, acsys.CS.SlipRatio)
    angles = ac.getCarState(car, acsys.CS.SlipAngle)
    return Snapshot(
        [Wheel(ratio, angle) for ratio, angle in zip(ratios, angles)],
        body_slip(ac.getCarState(car, acsys.CS.LocalVelocity)),
    )

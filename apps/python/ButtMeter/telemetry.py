import math

import ac, acsys


class Wheel:
    def __init__(self, slip_ratio: float, slip_angle: float) -> None:
        self.slip_ratio = slip_ratio
        self.slip_angle = slip_angle


class Wheels:
    def __init__(self, fl: Wheel, fr: Wheel, rl: Wheel, rr: Wheel) -> None:
        self.front_left = fl
        self.front_right = fr
        self.rear_left = rl
        self.rear_right = rr


def body_slip(velocity: list) -> float:
    lateral, _, forward = velocity
    if math.hypot(lateral, forward) < 2.0:
        return 0.0
    return math.degrees(math.atan2(lateral, forward))


class Snapshot:
    def __init__(self, speed: float, wheels: list, body_slip: float) -> None:
        self.speed = speed
        self.wheels = wheels
        self.body_slip = body_slip


def read_snapshot() -> Snapshot:
    car = ac.getFocusedCar()
    ratios = ac.getCarState(car, acsys.CS.SlipRatio)
    angles = ac.getCarState(car, acsys.CS.SlipAngle)
    return Snapshot(
        ac.getCarState(car, acsys.CS.SpeedKMH),
        [Wheel(ratio, angle) for ratio, angle in zip(ratios, angles)],
        body_slip(ac.getCarState(car, acsys.CS.LocalVelocity)),
    )

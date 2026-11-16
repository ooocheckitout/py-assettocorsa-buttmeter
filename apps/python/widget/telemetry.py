import math

import ac
import acsys


class WheelSlips:
    def __init__(
        self, front_left: float, front_right: float, rear_left: float, rear_right: float
    ) -> None:
        self.front_left = front_left
        self.front_right = front_right
        self.rear_left = rear_left
        self.rear_right = rear_right


class Telemetry:
    def __init__(
        self, slip_ratios: WheelSlips, slip_angles: WheelSlips, yaw_rate: float
    ) -> None:
        self.slip_ratios = slip_ratios
        self.slip_angles = slip_angles
        self.yaw_rate = yaw_rate


def idle_wheel_slips() -> WheelSlips:
    return WheelSlips(0.0, 0.0, 0.0, 0.0)


def idle_telemetry() -> Telemetry:
    return Telemetry(idle_wheel_slips(), idle_wheel_slips(), 0.0)


def read_wheel_slips(car: int, state: int) -> WheelSlips:
    fl, fr, rl, rr = ac.getCarState(car, state)
    return WheelSlips(fl, fr, rl, rr)


def read_telemetry() -> Telemetry:
    car = ac.getFocusedCar()
    _, yaw, _ = ac.getCarState(car, acsys.CS.LocalAngularVelocity)
    return Telemetry(
        read_wheel_slips(car, acsys.CS.SlipRatio),
        read_wheel_slips(car, acsys.CS.SlipAngle),
        math.degrees(yaw),
    )

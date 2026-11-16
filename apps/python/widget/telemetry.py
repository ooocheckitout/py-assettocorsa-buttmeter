import ac
import acsys


class WheelSlips:
    def __init__(self, front_left: float, front_right: float, rear_left: float,
                 rear_right: float) -> None:
        self.front_left = front_left
        self.front_right = front_right
        self.rear_left = rear_left
        self.rear_right = rear_right


def idle_wheel_slips() -> WheelSlips:
    return WheelSlips(0.0, 0.0, 0.0, 0.0)


def read_wheel_slips() -> WheelSlips:
    car = ac.getFocusedCar()
    front_left, front_right, rear_left, rear_right = ac.getCarState(car, acsys.CS.SlipRatio)
    return WheelSlips(front_left, front_right, rear_left, rear_right)

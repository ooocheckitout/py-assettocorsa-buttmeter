import ac, acsys

# The app should be installed to: apps\python\{self.name}\{self.name}.py
# The icon is taken from: content\gui\icons\{self.name}_{ON,OFF}.png
# The logs are stored: Documents\Assetto Corsa\logs\py_log.txt


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


class Rotation:
    def __init__(self, pitch: float, yaw: float, roll: float) -> None:
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll


class Snapshot:
    def __init__(
        self, speed: float, wheels: Wheels, angular_velocity: Rotation
    ) -> None:
        self.speed = speed
        self.wheels = wheels
        self.angular_velocity = angular_velocity


def read_snapshot(car: int) -> Snapshot:
    speed = ac.getCarState(car, acsys.CS.SpeedKMH)

    ratios = ac.getCarState(car, acsys.CS.SlipRatio)
    angles = ac.getCarState(car, acsys.CS.SlipAngle)
    wheels = Wheels(*[Wheel(ratio, angle) for ratio, angle in zip(ratios, angles)])

    pitch, yaw, roll = ac.getCarState(car, acsys.CS.LocalAngularVelocity)
    rotation = Rotation(pitch, yaw, roll)

    return Snapshot(speed, wheels, rotation)


class Component:
    def update(self) -> None:
        pass

    def render(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


components = []


def render_all(delta_time: float) -> None:
    ac.log("render_all {}".format(delta_time))

    for component in components:
        component.render()


def acMain(ac_version: str) -> str:
    """Runs once the session is loaded."""
    ac.log("acMain {}".format(ac_version))

    name = "widget"
    app_id = ac.newApp(name)

    ac.setSize(app_id, 600, 800)
    ac.addRenderCallback(app_id, render_all)

    return name


def acUpdate(delta_time_sec: float) -> None:
    """Runs every frame for the whole session."""
    ac.log("acUpdate {}".format(delta_time_sec))

    for component in components:
        component.update()


def acShutdown() -> None:
    """Runs once when the session ends normally."""
    ac.log("acShutdown")

    for component in components:
        component.shutdown()

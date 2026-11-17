import ac

from render import Component
from telemetry import read_snapshot


class Application:
    def __init__(self, name: str) -> None:
        self.name = name
        self.id = ac.newApp(name)
        self.components = []
        ac.addRenderCallback(self.id, self.render)

    def resize(self, width: float, height: float) -> None:
        ac.setSize(self.id, width, height)

    def frameless(self, opacity: float) -> None:
        ac.setTitle(self.id, "")
        ac.setIconPosition(self.id, 0, -10000)
        ac.setBackgroundOpacity(self.id, opacity)
        ac.drawBorder(self.id, 0)

    def add(self, component: Component) -> Component:
        self.components.append(component)
        return component

    def render(self, _: float) -> None:
        snapshot = read_snapshot()

        for component in self.components:
            component.update(snapshot)

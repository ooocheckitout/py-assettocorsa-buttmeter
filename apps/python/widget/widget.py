import os, sys

root = os.path.dirname(os.path.abspath(__file__))
for folder in ("", "apps", "components"):
    sys.path.insert(0, os.path.join(root, folder))
from settings import load_settings
from settings_application import SettingsApplication
from widget_application import WidgetApplication

# The app should be installed to: apps\python\{self.name}\{self.name}.py
# The icon is taken from: content\gui\icons\{self.name}_{ON,OFF}.png
# The logs are stored: Documents\Assetto Corsa\logs\py_log.txt


def acMain(_: str) -> str:
    """Runs once the session is loaded."""
    settings = load_settings()
    WidgetApplication(settings)
    SettingsApplication(settings)

    return "AlligatorRacing"

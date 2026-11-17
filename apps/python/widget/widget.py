import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from settings import load_settings
from apps.settings_application import SettingsApplication
from apps.widget_application import WidgetApplication

# The app should be installed to: apps\python\{self.name}\{self.name}.py
# The icon is taken from: content\gui\icons\{self.name}_{ON,OFF}.png
# The logs are stored: Documents\Assetto Corsa\logs\py_log.txt

applications = []


def acMain(_: str) -> str:
    """Runs once the session is loaded."""
    settings = load_settings()
    applications.append(WidgetApplication(settings))
    applications.append(SettingsApplication(settings))

    return "AlligatorRacing"

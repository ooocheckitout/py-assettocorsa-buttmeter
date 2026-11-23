import os, sys

app_directory = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_directory)

# CSP reload re-runs this file in the same interpreter; cached submodules would keep old code.
for module_name in list(sys.modules):
    if module_name == "buttmeter" or module_name.startswith("buttmeter."):
        del sys.modules[module_name]

from buttmeter.config import load_settings
from buttmeter.apps.settings import SettingsApplication
from buttmeter.apps.widget import WidgetApplication

settings = load_settings()
widget_app = WidgetApplication(settings)
settings_app = SettingsApplication(settings)


def acMain(_: str) -> str:
    """Runs once the session is loaded."""
    widget_app.initialize()
    settings_app.initialize()

    return "AlligatorRacing"

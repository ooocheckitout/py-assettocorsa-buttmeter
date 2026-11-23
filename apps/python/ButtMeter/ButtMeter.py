import os, sys

app_directory = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_directory)

# CSP reload re-runs this file in the same interpreter; cached submodules would keep old code.
for module_name, module in list(sys.modules.items()):
    if module_name != __name__ and os.path.abspath(getattr(module, "__file__", None) or "").startswith(app_directory + os.sep):
        del sys.modules[module_name]

from config import load_settings
from apps.settings import SettingsApplication
from apps.widget import WidgetApplication

# The app should be installed to: apps\python\{self.name}\{self.name}.py
# The icon is taken from: content\gui\icons\{self.name}_{ON,OFF}.png
# The logs are stored: Documents\Assetto Corsa\logs\py_log.txt

settings = load_settings()
widget_app = WidgetApplication(settings)
settings_app = SettingsApplication(settings)


def acMain(_: str) -> str:
    """Runs once the session is loaded."""
    widget_app.initialize()
    settings_app.initialize()

    return "AlligatorRacing"

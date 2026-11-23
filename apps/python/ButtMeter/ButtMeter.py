import os, sys

app_directory = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_directory)

# CSP reload re-runs this file in the same interpreter; cached submodules would keep old code.
for module_name, module in list(sys.modules.items()):
    is_self = module_name == __name__
    is_app_file = (getattr(module, "__file__", None) or "").startswith(app_directory + os.sep)
    if is_app_file and not is_self:
        del sys.modules[module_name]

from config import load_settings
from apps.settings import SettingsApplication
from apps.widget import WidgetApplication

settings = load_settings()
widget_app = WidgetApplication(settings)
settings_app = SettingsApplication(settings)


def acMain(_: str) -> str:
    """Runs once the session is loaded."""
    widget_app.initialize()
    settings_app.initialize()

    return "AlligatorRacing"

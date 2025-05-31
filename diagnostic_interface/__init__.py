from .config import settings
from widgets import TimedWidget, DataSelect
from dialog import SettingsDialog
from canvas import PlotCanvas, CustomNavigationToolbar
from tabs import PlotTab, WeatherTab
# from tabs import DockerStackTab, PlotTab

__all__ = [
    "TimedWidget",
    "SettingsDialog",
    "CustomNavigationToolbar",
    "PlotCanvas",
    "PlotTab",
    "WeatherTab",
    "DataSelect",
    # "DockerStackTab",
    "settings"
]

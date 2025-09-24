from .config import settings
from widgets import TimedWidget, DataSelect
from dialog import SettingsDialog
from canvas import PlotCanvas, CustomNavigationToolbar
from tabs import PlotTab
#from .copy import PlotTab2

# from tabs import DockerStackTab, PlotTab

__all__ = [
    "TimedWidget",
    "SettingsDialog",
    "CustomNavigationToolbar",
    "PlotCanvas",
    "PlotTab",
    #"PlotTab2",
    "DataSelect",
    # "DockerStackTab",
    "settings"
]

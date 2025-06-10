#from .config import settings, command_settings
# from .canvas.plot_canvas import PlotCanvas
# from .canvas.plot_canvas import PlotCanvas2
# from .canvas.plot_canvas import IntegralPlot
from .config import settings
from .config import command_settings
from widgets import TimedWidget, DataSelect
from dialog import SettingsDialog
from canvas import PlotCanvas, PlotCanvas2, IntegralPlot, CustomNavigationToolbar, RealtimeCanvas
from tabs import PlotTab, WeatherTab
# from tabs import DockerStackTab, PlotTab
from canvas import PlotCanvas, CustomNavigationToolbar
from tabs import DockerStackTab, PlotTab

__all__ = [
    "TimedWidget",
    "SettingsDialog",
    "CustomNavigationToolbar",
    "PlotCanvas",
    "RealtimeCanvas",
    "PlotCanvas2",
    "PlotTab",
    "IntegralPlot",
    "WeatherTab",
    "DataSelect",
    "DockerStackTab",
    "settings",
    "command_settings"
]

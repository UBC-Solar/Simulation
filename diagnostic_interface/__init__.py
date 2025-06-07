#from .canvas.plot_canvas import PlotCanvas, PlotCanvas2
#from .canvas.plot_canvas import PlotCanvas2
#from .canvas.plot_canvas import IntegralPlot
from .config import settings
from widgets import TimedWidget, DataSelect
from dialog import SettingsDialog
from canvas import PlotCanvas, PlotCanvas2, IntegralPlot, CustomNavigationToolbar
from tabs import PlotTab, WeatherTab
# from tabs import DockerStackTab, PlotTab

__all__ = [
    "TimedWidget",
    "SettingsDialog",
    "CustomNavigationToolbar",
    "PlotCanvas",
    "PlotCanvas2",
    "PlotTab",
    "IntegralPlot",
    "WeatherTab",
    "DataSelect",
    # "DockerStackTab",
    "settings"
]

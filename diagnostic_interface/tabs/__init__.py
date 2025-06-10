# from .docker_panel import DockerStackTab
#from diagnostic_interface import PlotTab

#from .plot_tab import WeatherTab
from .weather_tab import WeatherTab
from .plot_tab import PlotTab
from .docker_panel import DockerStackTab
from .plot_tab import PlotTab
from ._updatable import UpdatableTab
from .sunbeam_panel import SunbeamTab
from .sunlink_panel import SunlinkTab
from .telemetry_panel import TelemetryTab
from .soc_tab import SOCTab

__all__ = [
    "DockerStackTab",
    "PlotTab",
    #"PlotTab",
    "UpdatableTab",
    "WeatherTab",
    # "SunbeamTab",
    # "SunlinkTab",
    # "TelemetryTab"
    "SunbeamTab",
    "SunlinkTab",
    "TelemetryTab",
    "SOCTab"
]

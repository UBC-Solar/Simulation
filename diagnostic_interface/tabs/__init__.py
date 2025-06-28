# from .docker_panel import DockerStackTab
#from diagnostic_interface import PlotTab

#from .plot_tab import WeatherTab
#from .weather_tab import WeatherTab
from .plot_tab import PlotTab
from .docker_panel import DockerStackTab
from .weather_tab import WeatherTab
from ._updatable import UpdatableTab
from .power_panel import PowerTab
from .sunbeam_panel import SunbeamTab
from .sunlink_panel import SunlinkTab
from .telemetry_panel import TelemetryTab
from .soc_tab import SOCTab

__all__ = [
    "DockerStackTab",
    "PlotTab",
    "WeatherTab",
    "UpdatableTab",
    "SunbeamTab",
    "SunlinkTab",
    "TelemetryTab",
    "PowerTab",
    "SOCTab"
]

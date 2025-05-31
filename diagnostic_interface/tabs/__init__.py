# from .docker_panel import DockerStackTab
#from diagnostic_interface import PlotTab

from .plot_tab import WeatherTab
#from .plot_tab import PlotTab
from ._updatable import UpdatableTab
from .copy import PlotTab2
# from .sunbeam_panel import SunbeamTab
# from .sunlink_panel import SunlinkTab
# from .telemetry_panel import TelemetryTab

__all__ = [
    # "DockerStackTab",
    "PlotTab2",
    #"PlotTab",
    "UpdatableTab",
    "PlotTab2"
    # "SunbeamTab",
    # "SunlinkTab",
    # "TelemetryTab"
]

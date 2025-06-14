from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox,
    QGroupBox, QHBoxLayout, QLabel
)
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot
#from poetry.console.commands import self

from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, PlotCanvas, PlotCanvas2, IntegralPlot, RealtimeCanvas



HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}

EVENT = "FSGP_2024_Day_1"


class PlotRefreshWorkerSignals2(QObject):
    finished = pyqtSignal(bool)

class PlotRefreshWorker2(QRunnable):
    def __init__(self, plot_canvas):
        super().__init__()

        self.plot_canvas = plot_canvas
        self.signals = PlotRefreshWorkerSignals2()


    def run(self):
        success = self.plot_canvas.query_and_plot()
        self.signals.finished.emit(success)





class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object, object)  # emits the TimeSeries
    error = pyqtSignal(str)  # emits an error message


class PlotRefreshWorker(QRunnable):
    def __init__(self, plot_canvas: RealtimeCanvas, plot_canvas2: PlotCanvas2):
        super().__init__()
        self.plot_canvas: RealtimeCanvas = plot_canvas
        self.plot_canvas2: PlotCanvas2 = plot_canvas2
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:
            plot_canvas1 = self.plot_canvas.fetch_data()
            plot_canvas2 = self.plot_canvas2
            self.signals.data_ready.emit(plot_canvas1, plot_canvas2)

        except Exception as e:
            print(e)
            self.signals.error.emit(str(e))




###

class WeatherTab(QWidget):
    close_requested = pyqtSignal(QWidget)

    def __init__(self, parent = None):

        super().__init__(parent)
        self._thread_pool = QThreadPool()

        # Layout setup
        #self.layout = QVBoxLayout(self)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(30, 30, 30, 30)


        #plots

        plot1_layout = QVBoxLayout()

        self.plot_canvas1 = RealtimeCanvas("weather", "GHI")

        self.data_name = "GHI"

        self.toolbar1 = CustomNavigationToolbar(canvas=self.plot_canvas1)
        plot1_layout.addWidget(self.toolbar1)
        plot1_layout.addWidget(self.plot_canvas1)


        plot2_layout = QVBoxLayout()

        self.plot_canvas2 = PlotCanvas2()
        self.toolbar2 = CustomNavigationToolbar(canvas=self.plot_canvas2)

        plot2_layout.addWidget(self.toolbar2)
        plot2_layout.addWidget(self.plot_canvas2)



        plot3_layout = QVBoxLayout()

        self.plot_canvas3 = IntegralPlot(self)
        self.toolbar3 = CustomNavigationToolbar(canvas=self.plot_canvas3)
        plot3_layout.addWidget(self.toolbar3)
        plot3_layout.addWidget(self.plot_canvas3)


       # self.label = QLabel("add text")

        bottom_plots_layout = QHBoxLayout()

        #bottom_plots_layout.addWidget(self.label)
        bottom_plots_layout.addLayout(plot2_layout)
        bottom_plots_layout.addLayout(plot3_layout)

        self.layout.addLayout(plot1_layout)
        self.layout.addLayout(bottom_plots_layout)



        # Buttons
        help_button = QPushButton("Help")
        help_button.setObjectName("helpButton")
        help_button.clicked.connect(lambda: self.show_help_message(self.data_name, self.event))

        button_group = QGroupBox("Actions")
        button_layout = QHBoxLayout()
        button_layout.addWidget(help_button)
        button_group.setLayout(button_layout)

        self.layout.addWidget(button_group)

        self.setStyleSheet("""
            QPushButton#helpButton, QPushButton#closeButton {
                padding: 6px 12px;
                border-radius: 8px;
            }
        """)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_plot)

#stuff added:




        plot1 = self.plot_canvas1.fetch_data()
        # plot2 = self.plot_canvas2.query_and_plot("production", "weather", "realtime", "WindSpeed10m")
        # self.plot_canvas2.query_and_plot("production", "weather", "realtime", "PrecipitationRate")

        plot2 = self.plot_canvas2
        plot3 = self.plot_canvas3.query_and_plot()

        #if not(plot1 and plot2 and plot3):
        if plot1 is None:
            self.request_close()

    def set_tab_active(self, active: bool) -> None:
        if active:
            self.refresh_timer.setInterval(settings.plot_timer_interval * 1000)
            self.refresh_timer.start()
            QTimer.singleShot(0, self.refresh_plot)

        else:
            self.refresh_timer.stop()

    def refresh_plot(self):


        worker = PlotRefreshWorker(self.plot_canvas1, self.plot_canvas2)
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self._thread_pool.start(worker)

        worker3 = PlotRefreshWorker2(self.plot_canvas3)
        worker3.signals.finished.connect(self._on_plot_refresh_finished)
        self._thread_pool.start(worker3)










    @pyqtSlot(object, object)
    def _on_data_ready(self, plot_canvas1, plot_canvas2):
        self.plot_canvas1.plot(plot_canvas2, f"", "SOC (%)")
        self.unfiltered_soc_canvas.plot(unfiltered_soc, f"Unfiltered SOC", "SOC (%)")

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)

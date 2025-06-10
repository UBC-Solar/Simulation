from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox,
    QGroupBox, QHBoxLayout, QLabel
)
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer
#from poetry.console.commands import self

from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, PlotCanvas, PlotCanvas2, IntegralPlot



HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}

EVENT = "FSGP_2024_Day_1"


# class PlotRefreshWorkerSignals(QObject):
#     finished = pyqtSignal(bool)  # success or failure
#

class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object)  # emits the TimeSeries
    error = pyqtSignal(str)  # emits an error message


# class PlotRefreshWorker(QRunnable):
#     def __init__(self, plot_canvas, origin, source, event, data_name):
#     #def __init__(self, plot_canvas):
#         super().__init__()
#         self.plot_canvas = plot_canvas
#         self.origin = origin
#         self.source = source
#         self.event = event
#         self.data_name = data_name
#         self.signals = PlotRefreshWorkerSignals()
#
#     def run(self):
#         success = self.plot_canvas.query_and_plot(self.origin, self.source, self.event, self.data_name)
#         self.signals.finished.emit(success)


class PlotRefreshWorker(QRunnable):
    def __init__(self, canvas: PlotCanvas ):
        super().__init__()
        self.canvas: PlotCanvas = canvas

        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:

            ts = self.canvas.fetch_data()
            self.signals.data_ready.emit(ts)

        except Exception as e:
            self.signals.error.emit(str(e))




 ##

class PlotRefreshWorker2(QRunnable):
    def __init__(self, plot_canvas):
        super().__init__()
        #self.plot_canvas = plot_canvas

        self.plot_canvas = plot_canvas
        # self.origin = origin
        # self.source = source
        # self.event = event
        # self.data_name = data_name
        self.signals = PlotRefreshWorkerSignals()


    def run(self):
        #success = self.plot_canvas.query_and_plot(self.origin, self.source, self.event, self.data_name)
        success = self.plot_canvas.query_and_plot()
        self.signals.finished.emit(success)




class PlotTab(QWidget):
    close_requested = pyqtSignal(QWidget)

    def __init__(self, origin: str, source: str, event: str, data_name: str, parent=None):
        super().__init__(parent)

        self.origin = origin
        self.source = source
        self.event = event
        self.data_name = data_name

        self._thread_pool = QThreadPool()

        # Layout setup
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)

        self.plot_canvas = PlotCanvas(self)
        self.toolbar = CustomNavigationToolbar(canvas=self.plot_canvas)

        # Buttons
        help_button = QPushButton("Help")
        help_button.setObjectName("helpButton")
        help_button.clicked.connect(lambda: self.show_help_message(data_name, event))

        close_button = QPushButton("Close Tab")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.request_close)

        button_group = QGroupBox("Actions")
        button_layout = QHBoxLayout()
        button_layout.addWidget(help_button)
        button_layout.addWidget(close_button)
        button_group.setLayout(button_layout)

        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.plot_canvas)
        self.layout.addWidget(button_group)

        self.setStyleSheet("""
            QPushButton#helpButton, QPushButton#closeButton {
                padding: 6px 12px;
                border-radius: 8px;
            }
        """)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_plot)

        if not self.plot_canvas.query_and_plot(self.origin, self.source, self.event, self.data_name):
            self.request_close()

    def set_tab_active(self, active: bool) -> None:
        if active:
            self.refresh_timer.setInterval(settings.plot_timer_interval * 1000)
            self.refresh_timer.start()
            QTimer.singleShot(0, self.refresh_plot)

        else:
            self.refresh_timer.stop()

    def refresh_plot(self):
        worker = PlotRefreshWorker(
            self.plot_canvas,
            self.origin,
            self.source,
            self.event,
            self.data_name
        )
        worker.signals.finished.connect(self._on_plot_refresh_finished)
        self._thread_pool.start(worker)

    def _on_plot_refresh_finished(self, success: bool):
        if not success:
            self.request_close()

    def request_close(self):
        self.close_requested.emit(self)

    def show_help_message(self, data_name, event):
        message = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")
        QMessageBox.information(self, f"Help: {data_name}", message)




#


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

        self.plot_canvas1 = PlotCanvas(self)
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



        plot1 = self.plot_canvas1.query_and_plot("production", "weather", "realtime", "GHI")

        plot2 = self.plot_canvas2
        plot3 = self.plot_canvas3

        if not (plot1 and plot2 and plot3):
            self.request_close()

    def set_tab_active(self, active: bool) -> None:
        if active:
            self.refresh_timer.setInterval(settings.plot_timer_interval * 1000)
            self.refresh_timer.start()
            QTimer.singleShot(0, self.refresh_plot)

        else:
            self.refresh_timer.stop()

    def refresh_plot(self):


        worker1 = PlotRefreshWorker(self.plot_canvas1, "production", "weather", "realtime", "GHI")

        worker1.signals.finished.connect(self._on_plot_refresh_finished)
        self._thread_pool.start(worker1)


        worker2 = PlotRefreshWorker(self.plot_canvas2, "production", "weather", "realtime", "WindSpeed10m")
        worker_add = PlotRefreshWorker(self.plot_canvas2, "production", "weather", "realtime", "PrecipitationRate")
        worker2.signals.finished.connect(self._on_plot_refresh_finished)
        worker_add.signals.finished.connect(self._on_plot_refresh_finished)
        self._thread_pool.start(worker2)
        self._thread_pool.start(worker_add)


        worker3 = PlotRefreshWorker2(self.plot_canvas3)
        worker3.signals.finished.connect(self._on_plot_refresh_finished)
        self._thread_pool.start(worker3)

    def _on_plot_refresh_finished(self, success: bool):
        if not success:
            self.request_close()

    def request_close(self):
        self.close_requested.emit(self)

    def show_help_message(self, data_name):
        message1 = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")
        QMessageBox.information(self, f"Help: {data_name}", message1)












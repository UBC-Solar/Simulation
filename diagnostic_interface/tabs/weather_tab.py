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

#
# class PlotRefreshWorkerSignals(QObject):
#     finished = pyqtSignal(bool)  # success or failure
#
# class PlotRefreshWorker(QRunnable):
#     def __init__(self, plot_canvas, origin, source, event, data_name):
#         super().__init__()
#         #self.plot_canvas = plot_canvas
#
#         self.plot_canvas = plot_canvas
#         self.origin = origin
#         self.source = source
#         self.event = event
#         self.data_name = data_name
#         self.signals = PlotRefreshWorkerSignals()
#
#
#     def run(self):
#         #success = self.plot_canvas.query_and_plot(self.origin, self.source, self.event, self.data_name)
#         success = self.plot_canvas.fetch_data()
#         self.signals.finished.emit(success)


class PlotRefreshWorker(QRunnable):
    def __init__(self, plot_canvas: RealtimeCanvas, plot_canvas2: PlotCanvas2):
        super().__init__()
        self.plot_canvas: RealtimeCanvas = plot_canvas
        self.plot_canvas2: PlotCanvas2 = plot_canvas2
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        try:
            plot1 = self.plot_canvas.fetch_data()

            # this one does the fetching + plotting together
            success = self.plot_canvas2.query_and_plot("production", "weather", "realtime", "WindSpeed10m")

            if not success:
                raise RuntimeError("PlotCanvas2 failed to fetch or plot.")

            self.signals.data_ready.emit(plot1, None)  # Only plot1 passed here

        except Exception as e:
            print(e)
            self.signals.error.emit(str(e))


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



       # plot1 = self.plot_canvas1.query_and_plot("production", "weather", "realtime", "GHI")
        plot1 = self.plot_canvas1.fetch_data()
        # plot2 = self.plot_canvas2.query_and_plot("production", "weather", "realtime", "WindSpeed10m")
        # self.plot_canvas2.query_and_plot("production", "weather", "realtime", "PrecipitationRate")
        plot2 = self.plot_canvas2
        plot3 = self.plot_canvas3

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


        #worker1 = PlotRefreshWorker(self.plot_canvas1, "production", "weather", "realtime", "GHI")

        worker = PlotRefreshWorker(self.plot_canvas1, self.plot_canvas2)
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self._thread_pool.start(worker)







    # @pyqtSlot(object, object)
    # def _on_data_ready(self, plot_canvas1, plot_canvas2):
    #     #self.plot_canvas1.plot(plot_canvas1, plot_canvas2, f"SOC", "SOC (%)")
    #     self.plot_canvas1.plot(plot_canvas1, "GHI", "GHI Realtime")
    #
    #     #self.plot_canvas3.plot3(plot_canvas3, f"Unfiltered SOC", "SOC (%)")

    @pyqtSlot(object, object)
    def _on_data_ready(self, plot1_data, _unused):
        self.plot_canvas1.plot(plot1_data, "GHI", "Irradiance (W/m²)")
        # plot_canvas2 already plotted internally

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)

    def _on_plot_refresh_finished(self, success: bool):
        if not success:
            self.request_close()

    def request_close(self):
        self.close_requested.emit(self)

    def show_help_message(self, data_name):
        message1 = HELP_MESSAGES.get(data_name, "No specific help available for this plot.")
        QMessageBox.information(self, f"Help: {data_name}", message1)













# class SOCTab(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.origin = settings.realtime_pipeline
#         self.source = "energy"
#         self.event = settings.realtime_event
#         self.data_name = "SOC"
#
#         self.pool = QThreadPool()
#         self.layout = QVBoxLayout(self)
#         self.soc_canvas = RealtimeCanvas("energy", "SOC")
#         self.unfiltered_soc_canvas = RealtimeCanvas("energy", "UnfilteredSOC")
#         self.soc_toolbar = CustomNavigationToolbar(canvas=self.soc_canvas)
#         self.unfiltered_soc_toolbar = CustomNavigationToolbar(canvas=self.unfiltered_soc_canvas)
#
#         self.upper_plot_layout = QVBoxLayout()
#
#         self.upper_plot_layout.addWidget(self.soc_toolbar)
#         self.upper_plot_layout.addWidget(self.soc_canvas)
#
#         self.layout.addLayout(self.upper_plot_layout, stretch=3)
#
#         self.lower_layout = QHBoxLayout()
#
#         self.lower_plot_layout = QVBoxLayout()
#         self.lower_plot_layout.addWidget(self.unfiltered_soc_toolbar)
#         self.lower_plot_layout.addWidget(self.unfiltered_soc_canvas)
#
#         self.lower_layout.addLayout(self.lower_plot_layout)
#
#         self.text_layout = QVBoxLayout()
#
#         self.text_widget1 = QTextEdit()
#         self.text_widget2 = QTextEdit()
#         self.text_widget3 = QTextEdit()
#
#         self.text_layout.addWidget(self.text_widget1)
#         self.text_layout.addWidget(self.text_widget2)
#         self.text_layout.addWidget(self.text_widget3)
#
#         self.lower_layout.addLayout(self.text_layout)
#
#         self.layout.addLayout(self.lower_layout, stretch=2)
#
#         # one-off & repeating timer, interval in milliseconds
#         QTimer.singleShot(0, self.refresh_plot)
#
#         self.timer = QTimer(self)
#         self.timer.timeout.connect(self.refresh_plot)
#         self.timer.start(settings.plot_timer_interval * 1000)
#
#     def refresh_plot(self):
#         worker = PlotRefreshWorker(self.soc_canvas, self.unfiltered_soc_canvas)
#         worker.signals.data_ready.connect(self._on_data_ready)
#         worker.signals.error.connect(self._on_data_error)
#         self.pool.start(worker)
#
#     @pyqtSlot(object, object)
#     def _on_data_ready(self, soc, unfiltered_soc):
#         self.soc_canvas.plot(soc, f"SOC", "SOC (%)")
#         self.unfiltered_soc_canvas.plot(unfiltered_soc, f"Unfiltered SOC", "SOC (%)")
#
#     @pyqtSlot(str)
#     def _on_data_error(self, msg):
#         QMessageBox.critical(self, "Plot Error", msg)
#
#
#
#

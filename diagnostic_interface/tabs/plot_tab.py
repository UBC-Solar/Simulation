from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox,
    QGroupBox, QHBoxLayout
)
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer
#from poetry.console.commands import self

from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, PlotCanvas


HELP_MESSAGES = {
    "VehicleVelocity": "This plot shows velocity over time.\n\n"
                       "- X-axis: Time\n"
                       "- Y-axis: Velocity (m/s)\n"
                       "- Data is sourced from the car's telemetry system.\n",
}


class PlotRefreshWorkerSignals(QObject):
    finished = pyqtSignal(bool)  # success or failure


class PlotRefreshWorker(QRunnable):
    def __init__(self, plot_canvas, origin, source, event, data_name):
    #def __init__(self, plot_canvas):
        super().__init__()
        self.plot_canvas = plot_canvas
        self.origin = origin
        self.source = source
        self.event = event
        self.data_name = data_name
        self.signals = PlotRefreshWorkerSignals()

    def run(self):
        success = self.plot_canvas.query_and_plot(self.origin, self.source, self.event, self.data_name)
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








class PlotTab2(QWidget):
    close_requested = pyqtSignal(QWidget)

    #def __init__(self, origin : str, source: str, event: str, data_name1: str, data_name2: str, parent=None):
    def __init__(self, origin = "production", source = "power", event = "FSGP_2024_Day_1", data_name1 = "PackPower", data_name2 = "MotorPower", parent = None):
        super().__init__(parent)
        #
        # self.origin = origin
        # self.source = source
        # self.event = event
        # self.data_name1 = data_name1
        # self.data_name2 = data_name2


        self._thread_pool = QThreadPool()

        # Layout setup
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(30, 30, 30, 30)

        self.plot_canvas1 = PlotCanvas(self)
        self.plot_canvas2 = PlotCanvas(self)

        self.toolbar1 = CustomNavigationToolbar(canvas=self.plot_canvas1)
        self.toolbar2 = CustomNavigationToolbar(canvas=self.plot_canvas2)
        # Buttons
        help_button = QPushButton("Help")
        help_button.setObjectName("helpButton")
        help_button.clicked.connect(lambda: self.show_help_message(self.data_name1, self.event))

        close_button = QPushButton("Close Tab")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.request_close)

        button_group = QGroupBox("Actions")
        button_layout = QHBoxLayout()
        button_layout.addWidget(help_button)
        button_layout.addWidget(close_button)
        button_group.setLayout(button_layout)

        self.layout.addWidget(self.toolbar1)
        self.layout.addWidget(self.plot_canvas1)
        self.layout.addWidget(self.toolbar2)
        self.layout.addWidget(self.plot_canvas2)

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


        #plot1 = self.plot_canvas1.query_and_plot(self.origin, self.source, self.event, self.data_name1)
        plot1 = self.plot_canvas1.query_and_plot("production", "power", "FSGP_2024_Day_1", "MotorPower")

        plot2 = self.plot_canvas2.query_and_plot("production", "power","FSGP_2024_Day_1", "PackPower")

        # if not self.plot_canvas1.query_and_plot(self.origin, self.source, self.event, self.data_name):
        #     self.request_close()

        if not (plot1 and plot2):
            self.request_close()

    def set_tab_active(self, active: bool) -> None:
        if active:
            self.refresh_timer.setInterval(settings.plot_timer_interval * 1000)
            self.refresh_timer.start()
            QTimer.singleShot(0, self.refresh_plot)

        else:
            self.refresh_timer.stop()

    def refresh_plot(self):
        worker1 = PlotRefreshWorker(
            self.plot_canvas1,
            self.origin,
            self.source,
            self.event,
            self.data_name1
            #"MotorPower"

        )

        worker1.signals.finished.connect(self._on_plot_refresh_finished)
        self._thread_pool.start(worker1)

        worker2 = PlotRefreshWorker(
            self.plot_canvas2,
            self.origin,
            self.source,
            self.event,
            self.data_name2
            #"PackPower"
        )
        worker2.signals.finished.connect(self._on_plot_refresh_finished)
        self._thread_pool.start(worker2)

    def _on_plot_refresh_finished(self, success: bool):
        if not success:
            self.request_close()

    def request_close(self):
        self.close_requested.emit(self)

    def show_help_message(self, data_name1):
        message1 = HELP_MESSAGES.get(data_name1, "No specific help available for this plot.")
        QMessageBox.information(self, f"Help: {data_name1}", message1)















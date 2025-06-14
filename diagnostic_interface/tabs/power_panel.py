import traceback
from data_tools.query import SunbeamClient
from data_tools.schema import UnwrappedError
from PyQt5.QtWidgets import QMessageBox, QPushButton, QLabel
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot
from diagnostic_interface import settings, coords
from diagnostic_interface.canvas import CustomNavigationToolbar, RealtimeCanvas
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from diagnostic_interface.widgets import FoliumMapWidget
import numpy as np


class PlotRefreshWorkerSignals(QObject):
    data_ready = pyqtSignal(object, object, object)
    error = pyqtSignal(str)


class PlotRefreshWorker(QRunnable):
    def __init__(self, power_canvas: RealtimeCanvas):
        super().__init__()
        self.signals = PlotRefreshWorkerSignals()
        self.power_canvas = power_canvas

    def run(self):
        try:
            client = SunbeamClient(settings.sunbeam_api_url)
            pipeline = settings.realtime_pipeline
            event = settings.realtime_event

            motor_power = self.power_canvas.fetch_data()

            gis_indices = client.get_file(pipeline, event, "localization", "TrackIndex")
            lap_numbers = client.get_file(pipeline, event, "localization", "LapIndex")

            self.signals.data_ready.emit(motor_power, gis_indices, lap_numbers)

        except Exception as e:
            print(e)
            self.signals.error.emit(str(e))


class PowerTab(QWidget):
    def __init__(self, font_size: int = 36, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.layout = QVBoxLayout()

        # First plot: Power vs Time
        self.power_canvas = RealtimeCanvas("power", "MotorPower")
        power_toolbar = CustomNavigationToolbar(self.power_canvas, self)

        self.layout.addWidget(power_toolbar)
        self.layout.addWidget(self.power_canvas, stretch=1)

        self.map_panel_layout = QHBoxLayout()

        self.map_widget_layout = QVBoxLayout()

        self.map_widget = FoliumMapWidget(coords)
        self.map_widget_layout.addWidget(self.map_widget, stretch=5)

        self.map_button_layout = QHBoxLayout()
        self.next_lap_button = QPushButton("Next Lap")
        self.next_lap_button.clicked.connect(self.next_lap)
        self.prev_lap_button = QPushButton("Previous Lap")
        self.prev_lap_button.clicked.connect(self.prev_lap)
        self.map_button_layout.addWidget(self.next_lap_button)
        self.map_button_layout.addWidget(self.prev_lap_button)

        self.map_widget_layout.addLayout(self.map_button_layout, stretch=1)
        self.map_panel_layout.addLayout(self.map_widget_layout, stretch=4)

        self.map_text_layout = QVBoxLayout()
        self.map_text_1 = QLabel("Current Lap: ?")
        self.map_text_2 = QLabel("Maximum Laps: ?")
        self.map_text_3 = QLabel("Total Energy: ?")

        self.map_text_1.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold;")
        self.map_text_2.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold;")
        self.map_text_3.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold;")

        self.map_text_layout.addWidget(self.map_text_1)
        self.map_text_layout.addWidget(self.map_text_2)
        self.map_text_layout.addWidget(self.map_text_3)
        self.map_panel_layout.addLayout(self.map_text_layout, stretch=1)

        self.layout.addLayout(self.map_panel_layout, stretch=3)

        self.line = None

        self.setLayout(self.layout)

        QTimer.singleShot(0, self.refresh_plot)

        self.pool = QThreadPool()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_plot)

        self.gis_indices = None
        self.lap_indices = None
        self.motor_power = None
        self.max_laps = None
        self.current_lap_number = 0

    def next_lap(self):
        if not self.current_lap_number + 1 > self.max_laps:
            self.current_lap_number += 1
            self.draw_map()

        else:
            QMessageBox.warning(None, "Lap Error", f"There is no lap available after {self.max_laps}.")

    def prev_lap(self):
        if not self.current_lap_number < 1:
            self.current_lap_number -= 1
            self.draw_map()

        else:
            QMessageBox.warning(None, "Lap Error", "There is no lap available before 0.")

    def refresh_plot(self):
        worker = PlotRefreshWorker(self.power_canvas)
        worker.signals.data_ready.connect(self._on_data_ready)
        worker.signals.error.connect(self._on_data_error)
        self.pool.start(worker)

    def set_tab_active(self, active: bool) -> None:
        if active:
            self.timer.setInterval(settings.plot_timer_interval * 1000)
            self.timer.start()
            QTimer.singleShot(0, self.refresh_plot)

        else:
            self.timer.stop()

    def draw_map(self):
        current_lap_mask = self.lap_indices == self.current_lap_number

        energy = np.empty(len(coords), dtype=float)

        for i in range(len(coords)):
            current_gis_indices = np.logical_and(self.gis_indices == i, current_lap_mask)
            energy_used = np.sum(self.motor_power[current_gis_indices] * self.motor_power.period, axis=0)

            energy[i] = energy_used

        self.map_widget.update_map(energy, "J")
        self.map_text_1.setText(f"Current Lap: {self.current_lap_number}")
        self.map_text_2.setText(f"Maximum Laps: {self.max_laps}")
        self.map_text_3.setText(f"Total Energy: {np.sum(energy) / 1e3:.1f} kJ")

    @pyqtSlot(object, object, object)
    def _on_data_ready(self, motor_power, gis_indices_result, lap_numbers_result):
        try:
            self.motor_power = motor_power
            self.power_canvas.plot(motor_power, "Motor Power", "Power (W)")

            try:

                if self.max_laps is None:
                    draw_map = True
                else:
                    draw_map = False

                self.gis_indices = gis_indices_result.unwrap().data
                self.lap_indices = lap_numbers_result.unwrap().data
                self.max_laps = int(np.nanmax(self.lap_indices))

                if draw_map:
                    self.draw_map()

            except UnwrappedError:
                pass

        except UnwrappedError as e:
            traceback.print_exc()
            QMessageBox.critical(
                self.parent,
                "Power Tab Error",
                f"Failed to load power plots.\n\n{str(e)}"
            )

    @pyqtSlot(str)
    def _on_data_error(self, msg):
        QMessageBox.critical(self, "Plot Error", msg)


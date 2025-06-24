import traceback
from data_tools.query import SunbeamClient
from data_tools.schema import UnwrappedError
from PyQt5.QtWidgets import QMessageBox, QPushButton, QLabel
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject, QTimer, pyqtSlot, QTime, QDate, QDateTime
from diagnostic_interface import settings
from diagnostic_interface.canvas import CustomNavigationToolbar, RealtimeCanvas
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTimeEdit
from diagnostic_interface.widgets import RealtimeMapWidget
import numpy as np
from data_tools.collections import TimeSeries


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

            gps_longitude = client.get_file(pipeline, event, "localization", "GPSLongitude")
            gps_latitude = client.get_file(pipeline, event, "localization", "GPSLatitude")

            self.signals.data_ready.emit(motor_power, gps_longitude, gps_latitude)

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

        self.map_widget = RealtimeMapWidget(15.5 if "FSGP" in settings.realtime_event else 17.5)
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

        # Time-begin editor
        self.time_begin = QTimeEdit()
        self.time_begin.setDisplayFormat("HH:mm:ss")
        self.time_begin.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold;")
        self.time_begin.timeChanged.connect(self.on_time_begin_changed)
        self.time_begin.setKeyboardTracking(False)

        # Time-end editor
        self.time_end = QTimeEdit()
        self.time_end.setDisplayFormat("HH:mm:ss")
        self.time_end.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold;")
        self.time_end.timeChanged.connect(self.on_time_end_changed)
        self.time_end.setKeyboardTracking(False)

        # Total energy stays a label
        self.map_text_3 = QLabel("Total Energy: ?")
        self.map_text_3.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold;")

        # pack them into the layout
        self.map_text_layout.addWidget(self.time_begin)
        self.map_text_layout.addWidget(self.time_end)
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
        self.start_time = None
        self.end_time = None
        self.current_lap_number = 36
        self.time_difference = 60
        self.date = None

    def on_time_begin_changed(self, new_time: QTime):
        self.start_time = new_time
        self.draw_map()

    def on_time_end_changed(self, new_time: QTime):
        self.end_time = new_time
        self.draw_map()

    def next_lap(self):
        start = self.time_begin.time()
        end = self.time_end.time()
        diff = start.secsTo(end)

        if diff <= 0:
            QMessageBox.warning(self, "Invalid Interval",
                                "Cannot advance when end ≤ start.")
            return

        new_start = end
        new_end = end.addSecs(diff)

        # ensure still within the allowed window
        if new_start < self.minimum_time or new_end > self.maximum_time:
            QMessageBox.warning(self, "Out of Range",
                                f"Advancing by {diff}s would exceed allowed times "
                                f"({self.minimum_time.toString()}–{self.maximum_time.toString()}).")
            return

        # apply without firing intermediate recalcs
        self.time_begin.blockSignals(True)
        self.time_end.blockSignals(True)

        self.time_begin.setTime(new_start)
        self.time_end.setTime(new_end)

        self.time_begin.blockSignals(False)
        self.time_end.blockSignals(False)

        self.draw_map()

    def prev_lap(self):
        start = self.time_begin.time()
        end = self.time_end.time()
        diff = -start.secsTo(end)

        if diff >= 0:
            QMessageBox.warning(self, "Invalid Interval",
                                "Cannot advance when end ≤ start.")
            return

        new_start = start.addSecs(diff)
        new_end = start

        # ensure still within the allowed window
        if new_start < self.minimum_time or new_end > self.maximum_time:
            QMessageBox.warning(self, "Out of Range",
                                f"Advancing by {diff}s would exceed allowed times "
                                f"({self.minimum_time.toString()}–{self.maximum_time.toString()}).")
            return

        # apply without firing intermediate recalcs
        self.time_begin.blockSignals(True)
        self.time_end.blockSignals(True)

        self.time_begin.setTime(new_start)
        self.time_end.setTime(new_end)

        self.time_begin.blockSignals(False)
        self.time_end.blockSignals(False)

        self.draw_map()

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
        if (self.motor_power is not None) and (self.gps_longitude is not None) and (self.gps_latitude is not None) and (self.start_time is not None) and (self.end_time is not None) and (self.date is not None):
            current_lap_time = QDateTime(self.date, self.time_end.time()).toPyDateTime()
            previous_lap_time = QDateTime(self.date, self.time_begin.time()).toPyDateTime()

            current_lap_time_relative = current_lap_time.timestamp() - self.initial_time.timestamp()
            previous_lap_time_relative = previous_lap_time.timestamp() - self.initial_time.timestamp()

            try:
                current_index = self.gps_latitude.index_of(current_lap_time_relative)
            except ValueError:
                return

            try:
                previous_index = self.gps_latitude.index_of(previous_lap_time_relative)
            except ValueError:
                previous_index = 0

            latitudes = self.gps_latitude[previous_index:current_index]
            longitudes = -self.gps_longitude[previous_index:current_index]
            power = self.motor_power[previous_index:current_index]

            energy = power * power.period

            try:
                self.map_widget.update_map(energy, latitudes=latitudes, longitudes=longitudes, units="J", map_centroid=self.map_centroid)
            except ValueError:
                return

            self.map_text_3.setText(f"Total Energy: {np.sum(energy) / 1e3:.1f} kJ")

    @pyqtSlot(object, object, object)
    def _on_data_ready(self, motor_power, gps_longitude_result, gps_latitude_result):
        try:
            self.motor_power = motor_power

            try:
                gps_longitude_unaligned: TimeSeries = gps_longitude_result.unwrap().data
                gps_latitude_unaligned: TimeSeries = gps_latitude_result.unwrap().data

                tzinfo: TimeSeries = motor_power._start.tzinfo

                print(f"Motor Power tzinfo: {tzinfo}")

                gps_longitude_unaligned._stop = gps_longitude_unaligned._stop.replace(tzinfo=tzinfo)
                gps_latitude_unaligned._stop = gps_latitude_unaligned._stop.replace(tzinfo=tzinfo)
                gps_longitude_unaligned._start = gps_longitude_unaligned._start.replace(tzinfo=tzinfo)
                gps_latitude_unaligned._start = gps_latitude_unaligned._start.replace(tzinfo=tzinfo)

                self.gps_longitude, self.gps_latitude, self.motor_power = TimeSeries.align(gps_longitude_unaligned,
                                                                                              gps_latitude_unaligned,
                                                                                              self.motor_power)

                self.map_centroid = [np.mean(self.gps_latitude), -np.mean(self.gps_longitude)]

                self.gps_longitude._stop = self.gps_longitude._stop.replace(tzinfo=tzinfo)
                self.gps_latitude._stop = self.gps_latitude._stop.replace(tzinfo=tzinfo)
                self.gps_longitude._start = self.gps_longitude._start.replace(tzinfo=tzinfo)
                self.gps_latitude._stop = self.gps_latitude._stop.replace(tzinfo=tzinfo)

                self.initial_time = self.gps_longitude.datetime_x_axis[0]

                self.maximum_time = QTime(self.gps_longitude._stop.hour, self.gps_longitude._stop.minute, self.gps_longitude._stop.second)
                self.minimum_time = QTime(self.gps_longitude._start.hour, self.gps_longitude._start.minute, self.gps_longitude._start.second)

                self.time_begin.setMinimumTime(self.minimum_time)
                self.time_begin.setMaximumTime(self.maximum_time)
                #
                # self.time_end.setMinimumTime(self.minimum_time)
                self.time_end.setMaximumTime(self.maximum_time)

                self.date = QDate(self.gps_longitude._start.year, self.gps_longitude._start.month, self.gps_longitude._start.day)

                if self.start_time is None or self.end_time is None:
                    self.start_time = self.minimum_time
                    self.end_time = self.minimum_time.addSecs(60)

                    self.time_begin.blockSignals(True)
                    self.time_end.blockSignals(True)

                    self.time_begin.setTime(self.minimum_time)
                    self.time_end.setTime(self.minimum_time.addSecs(60))

                    self.time_begin.blockSignals(False)
                    self.time_end.blockSignals(False)

                    self.draw_map()

            except UnwrappedError:
                self.gps_longitude = None
                self.gps_latitude = None
                self.gps_indices = None

            self.power_canvas.plot(self.motor_power, "Motor Power", "Power (W)")

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
        self.timer.stop()

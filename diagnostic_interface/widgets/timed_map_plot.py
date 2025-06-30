from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QLabel, QDateTimeEdit
)
from PyQt5.QtCore import QDateTime
from diagnostic_interface import settings
from diagnostic_interface.widgets import RealtimeMapWidget

import numpy as np
from data_tools.schema import UnwrappedError
from data_tools.collections import TimeSeries

from datetime import datetime, timedelta

LOCAL_TZ = datetime.now().astimezone().tzinfo
MAX_WINDOW = timedelta(minutes=10)


class TimedMapPlot(QWidget):
    def __init__(self, font_size, transformer, reducer, horizontal=True, units="J", parent=None):
        super().__init__(parent)

        self.transformer = transformer
        self.reducer = reducer
        self.map_centroid = None
        self.units = units

        main_layout = QHBoxLayout() if horizontal else QVBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        self.map_widget = RealtimeMapWidget(
            15.5 if "FSGP" in settings.realtime_event else 17.5
        )
        left.addWidget(self.map_widget, stretch=5)

        btns = QHBoxLayout()
        for name, slot in (
                ("Previous", self.prev_lap),
                ("Next", self.next_lap)
        ):
            btn = QPushButton(name)
            btn.clicked.connect(slot)
            btns.addWidget(btn)
        left.addLayout(btns, stretch=1)

        # Datetime editor
        self.dt_begin = QDateTimeEdit(dateTime=QDateTime.currentDateTime())
        self.dt_end = QDateTimeEdit(dateTime=QDateTime.currentDateTime())
        for dt_edit in (self.dt_begin, self.dt_end):
            dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            dt_edit.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold;")
            dt_edit.dateTimeChanged.connect(self.draw_map)

        right.addWidget(QLabel("Start:"))
        right.addWidget(self.dt_begin)
        right.addWidget(QLabel("End:"))
        right.addWidget(self.dt_end)

        # Reduced value display
        self.lbl_energy = QLabel("Total Energy: ?")
        self.lbl_energy.setStyleSheet(f"font-size: {font_size}pt; font-weight: bold;")
        right.addWidget(self.lbl_energy)

        main_layout.addLayout(left, 4)
        main_layout.addLayout(right, 1)
        self.setLayout(main_layout)

        # --- internal state ---
        self.initial_time: datetime = None
        self.minimum_time: datetime = None
        self.maximum_time: datetime = None
        self.vertex_data = None
        self.gps_latitude = self.gps_longitude = None

    def next_lap(self):
        begin = self.get_begin_dt()
        end = self.get_end_dt()
        delta = end - begin
        if delta <= np.timedelta64(0, 's'):
            QMessageBox.warning(self, "Invalid Interval", "End must be after start.")
            return

        new_begin = end
        new_end = end + delta
        if new_begin < self.minimum_time or new_end > self.maximum_time:
            QMessageBox.warning(
                self, "Out of Range",
                f"Cannot advance by {delta}. Limits are "
                f"{self.minimum_time} – {self.maximum_time}."
            )
            return

        self.dt_begin.setDateTime(self.to_qt(new_begin))
        self.dt_end.setDateTime(self.to_qt(new_end))

    def prev_lap(self):
        begin = self.get_begin_dt()
        end = self.get_end_dt()
        delta = begin - end
        if delta >= np.timedelta64(0, 's'):
            QMessageBox.warning(self, "Invalid Interval", "Start must be before end.")
            return

        new_end = begin
        new_begin = begin - (end - begin)
        if new_begin < self.minimum_time or new_end > self.maximum_time:
            QMessageBox.warning(
                self, "Out of Range",
                f"Cannot rewind by {abs(delta)}. Limits are "
                f"{self.minimum_time} – {self.maximum_time}."
            )
            return

        self.dt_begin.setDateTime(self.to_qt(new_begin))
        self.dt_end.setDateTime(self.to_qt(new_end))

    def set_data(self, data, lat_res, lon_res):
        """Align three TimeSeries, record limits, and initialize editors."""
        try:
            lon_un = lon_res.unwrap().data
            lat_un = lat_res.unwrap().data

            # inherit tzinfo from data._start if present
            tz = data._start.tzinfo or LOCAL_TZ
            for ts in (lon_un, lat_un):
                ts._start = ts._start.replace(tzinfo=tz)
                ts._stop = ts._stop.replace(tzinfo=tz)

            self.gps_longitude, self.gps_latitude, self.vertex_data = \
                TimeSeries.align(lon_un, lat_un, data)

        except UnwrappedError:
            # fallback: only one series
            self.vertex_data = data
            self.gps_longitude = self.gps_latitude = None

        # Make everything tz-aware in local zone
        set_times = self.minimum_time is None
        self.initial_time = self.vertex_data._start.astimezone(LOCAL_TZ)
        self.minimum_time = self.vertex_data._start.astimezone(LOCAL_TZ)
        self.maximum_time = self.vertex_data._stop.astimezone(LOCAL_TZ)

        # Set editor bounds
        self.dt_begin.setMinimumDateTime(self.to_qt(self.minimum_time))
        self.dt_begin.setMaximumDateTime(self.to_qt(self.maximum_time))
        self.dt_end.setMinimumDateTime(self.to_qt(self.minimum_time))
        self.dt_end.setMaximumDateTime(self.to_qt(self.maximum_time))

        # Initialize a reasonable window
        if set_times:
            self.dt_begin.setDateTime(self.to_qt(self.minimum_time))
            self.dt_end.setDateTime(self.to_qt(self.minimum_time + np.timedelta64(60, 's')))

            # Trigger initial draw
            self.draw_map()

    def draw_map(self, *_):
        if self.vertex_data is None:
            return

        start_dt = self.get_begin_dt()
        end_dt = self.get_end_dt()
        rel_start = (start_dt - self.initial_time).total_seconds()
        rel_end = (end_dt - self.initial_time).total_seconds()

        delta = end_dt - start_dt
        if delta > MAX_WINDOW:
            # clamp end to start + MAX_WINDOW
            end_dt = start_dt + MAX_WINDOW - timedelta(seconds=1)
            # update the widget (without retriggering)
            self.dt_end.blockSignals(True)
            self.dt_end.setDateTime(self.to_qt(end_dt))
            self.dt_end.blockSignals(False)

        try:
            i0 = self.vertex_data.index_of(rel_start)
            i1 = self.vertex_data.index_of(rel_end)
        except ValueError:
            return

        # extract and plot
        segment = self.vertex_data[i0:i1]
        lat_seg = self.gps_latitude[i0:i1] if self.gps_latitude is not None else None
        lon_seg = -self.gps_longitude[i0:i1] if self.gps_longitude is not None else None

        transformed = self.transformer(segment)
        reduced = self.reducer(transformed)

        if lat_seg is not None and lon_seg is not None:
            try:
                self.map_widget.update_map(
                    transformed,
                    latitudes=lat_seg,
                    longitudes=lon_seg,
                    units=self.units,
                    map_centroid=self.map_centroid
                )
            except ValueError:
                pass

        self.lbl_energy.setText(str(reduced))

    def get_begin_dt(self) -> datetime:
        py = self.dt_begin.dateTime().toPyDateTime()  # naive local-time
        return py.replace(tzinfo=LOCAL_TZ)

    def get_end_dt(self) -> datetime:
        py = self.dt_end.dateTime().toPyDateTime()
        return py.replace(tzinfo=LOCAL_TZ)

    def to_qt(self, dt: datetime) -> QDateTime:
        # make sure it's in the local zone
        local = dt.astimezone(LOCAL_TZ)
        secs = int(local.timestamp())
        return QDateTime.fromSecsSinceEpoch(secs)

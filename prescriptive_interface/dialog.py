from typing import TypedDict
from PyQt5.QtWidgets import (
    QVBoxLayout, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QHBoxLayout, QPushButton, QCheckBox, QWidget, QButtonGroup
)
from diagnostic_interface.config import PersistentConfig
from datetime import datetime
from zoneinfo import ZoneInfo
from PyQt5.QtCore import Qt


class SimulationSettingsDict(TypedDict):
    race_type: str
    verbose: bool
    granularity: int
    car: str


class MultiToggleBar(QWidget):
    def __init__(self, labels, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

        self.group = QButtonGroup(self)
        self.group.setExclusive(False)

        for lbl in labels:
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setChecked(True)
            layout.addWidget(btn)
            self.group.addButton(btn)

    def not_selected(self):
        # returns list of labels currently checked
        return [b.text() for b in self.group.buttons() if not b.isChecked()]


class InitialConditionsDialog(QDialog):
    """Prompt the user to enter a starting SoC and time before running an optimization"""

    def __init__(self, initial_conditions: PersistentConfig, comp_start_date: datetime, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Optimization Initial Conditions")

        self.comp_start_date = comp_start_date

        # Create layout
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.soc_input = QLineEdit(str(initial_conditions.initial_battery_soc))

        start_time_layout = QHBoxLayout()
        self.start_time_input = QLineEdit(str(initial_conditions.start_time))
        get_time_button = QPushButton("Get Current Time")
        get_time_button.clicked.connect(self.fill_current_time)

        start_time_layout.addWidget(self.start_time_input)
        start_time_layout.addWidget(get_time_button)

        self.get_weather_checkbox = QCheckBox()

        form_layout.addRow("Initial SoC (0-1):", self.soc_input)
        form_layout.addRow("Start Time (s):", start_time_layout)
        form_layout.addRow("Get Weather:", self.get_weather_checkbox)

        self.days = MultiToggleBar([str(i) for i in [1, 2, 3]])
        form_layout.addRow("Days:", self.days)

        layout.addLayout(form_layout)

        # Add OK/Cancel buttons
        self.buttons = QDialogButtonBox(Qt.Horizontal)
        self.buttons.addButton(QPushButton(self.tr("&Go!")), QDialogButtonBox.AcceptRole)
        self.buttons.addButton(QPushButton(self.tr("&Cancel")), QDialogButtonBox.RejectRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def fill_current_time(self):
        """Fill start_time_input with seconds between now and comp_start_date"""
        now = datetime.now(tz=ZoneInfo("America/Chicago"))
        delta = now - self.comp_start_date
        self.start_time_input.setText(str(int(delta.total_seconds())))

    def get_values(self):
        try:
            initial_battery_soc = float(self.soc_input.text())
            start_time = int(self.start_time_input.text())
            get_weather = bool(self.get_weather_checkbox.isChecked())
            days = [int(i) - 1 for i in self.days.not_selected()]

            return initial_battery_soc, start_time, get_weather, days
        except ValueError:
            return None, None, None, None


class SettingsDialog(QDialog):
    """Settings tab where the user can change the population size and number of iterations of the optimization."""

    def __init__(self, popsize, maxiter, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Optimization Settings")

        # Create layout
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.popsize_input = QLineEdit(str(popsize))
        self.maxiter_input = QLineEdit(str(maxiter))

        form_layout.addRow("Population Size:", self.popsize_input)
        form_layout.addRow("Generation Limit:", self.maxiter_input)

        layout.addLayout(form_layout)

        # Add OK/Cancel buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def get_values(self):
        try:
            popsize = int(self.popsize_input.text())
            maxiter = int(self.maxiter_input.text())
            return popsize, maxiter
        except ValueError:
            return None, None

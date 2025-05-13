from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QSpinBox, QComboBox, QFormLayout

class SettingsDialog(QDialog):
    def __init__(self, current_interval, current_client_address, parent=None):
        """
        :param int current_interval: the current interval that is set on our timer.
        :param str current_client_address: the URL from where we are currently querying data.
        """
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 150)

        layout = QFormLayout()

        # Refresh interval selector
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(10, 3600)  # in seconds
        self.interval_spinbox.setValue(current_interval // 1000)  # convert ms to s
        layout.addRow("Refresh Interval (s):", self.interval_spinbox)

        # Client selector
        self.client_combo = QComboBox()
        self.client_combo.addItems(["SunbeamClient", "OtherClient"])  # Add more if needed
        self.client_combo.setCurrentText(current_client_address)
        layout.addRow("Data Client:", self.client_combo)

        # OK/Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_settings(self):
        return self.interval_spinbox.value(), self.client_combo.currentText()

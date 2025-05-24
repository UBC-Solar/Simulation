from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt
from diagnostic_interface.widgets import CommandOutputWidget
from diagnostic_interface import settings


class TelemetryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.running = False

        self._init_ui()

    def _init_ui(self):
        self.status_label = QLabel("❌ Status: Stopped")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.toggle_button = QPushButton("Start Telemetry")
        self.toggle_button.clicked.connect(self.toggle_stack)

        self.log_output = CommandOutputWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def toggle_stack(self):
        if self.running:
            self.stop_stack()
        else:
            self.start_stack()

    def start_stack(self):
        self.running = True
        self.status_label.setText("✅ Status: Running")

        self.log_output.start_in_venv(
            project_root=settings.sunlink_path,
            script_path="./link_telemetry.py",
            args=["-r", "can", "--debug"]
        )

        self.toggle_button.setText("Stop Telemetry")

    def stop_stack(self):
        self.running = False
        self.status_label.setText("❌ Status: Stopped")
        self.log_output.stop()
        self.toggle_button.setText("Start Telemetry")

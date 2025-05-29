from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QDialog
from PyQt5.QtCore import Qt
from diagnostic_interface.widgets import CommandOutputWidget
from diagnostic_interface.dialog import TextEditDialog
from diagnostic_interface.config import command_settings


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

        self.log_output = CommandOutputWidget(self.start_stack_command)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.log_output)

        edit_btn = QPushButton("Edit Commands", self)
        edit_btn.clicked.connect(self.open_edit_dialog)

        layout.addWidget(edit_btn)

        self.setLayout(layout)

    @staticmethod
    def start_stack_command() -> str:
        return command_settings.sunlink_up_cmd

    @staticmethod
    def open_edit_dialog():
        dlg = TextEditDialog([command_settings.telemetry_enable_cmd], ["Telemetry Link"])

        if dlg.exec_() == QDialog.Accepted:
            command_settings.telemetry_enable_cmd,  = dlg.getText()

    def toggle_stack(self):
        if self.running:
            self.stop_stack()
        else:
            self.start_stack()

    def start_stack(self):
        self.running = True
        self.status_label.setText("✅ Status: Running")

        cmd = command_settings.telemetry_enable_cmd

        self.log_output.start_cmd(cmd=cmd)

        self.toggle_button.setText("Stop Telemetry")

    def stop_stack(self):
        self.running = False
        self.status_label.setText("❌ Status: Stopped")
        self.log_output.stop()
        self.toggle_button.setText("Start Telemetry")

    def set_tab_active(self, active: bool):
        if active:
            self.log_output.activate()
        else:
            self.log_output.deactivate()

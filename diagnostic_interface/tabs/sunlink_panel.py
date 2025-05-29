from PyQt5.QtWidgets import QMessageBox, QPushButton, QDialog
from diagnostic_interface import settings
from diagnostic_interface.tabs import DockerStackTab
from abc import abstractmethod
from diagnostic_interface.dialog import TextEditDialog
from diagnostic_interface.config import command_settings


class SunlinkTab(DockerStackTab):
    def __init__(self):
        super().__init__()

        edit_btn = QPushButton("Edit Commands", self)
        edit_btn.clicked.connect(self.open_edit_dialog)

        self.layout.addWidget(edit_btn)

    @staticmethod
    def open_edit_dialog():
        dlg = TextEditDialog(
            [command_settings.sunlink_up_cmd, command_settings.sunlink_down_cmd],
            ["Sunlink Up", "Sunlink Down"]
        )

        if dlg.exec_() == QDialog.Accepted:
            command_settings.sunlink_up_cmd, command_settings.sunlink_down_cmd = dlg.getText()

    @staticmethod
    def start_stack_command():
        return command_settings.sunlink_up_cmd.split()

    @staticmethod
    def stop_stack_command():
        return command_settings.sunlink_down_cmd.split()

    @property
    def project_directory(self):
        return settings.sunlink_path

    def raise_docker_error(self):
        QMessageBox.critical(None, "Docker Error", f"Did not get a response from the Sunlink Docker service "
                                                   f"stack.\n Is Docker running and is Sunlink path correct? \n")

    @abstractmethod
    def evaluate_readiness(self, num_running_containers: int):
        if num_running_containers == 4:
            self.status_label.setText("✅ Status: 100%")
            self.stack_running = True

        else:
            self.status_label.setText(f"❌ Status: {int(num_running_containers / 4. * 100)}%")
            self.stack_running = True

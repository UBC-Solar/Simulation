from PyQt5.QtWidgets import QMessageBox, QPushButton, QDialog
from diagnostic_interface import settings
from diagnostic_interface.tabs import DockerStackTab
from diagnostic_interface.dialog import TextEditDialog
from data_tools.query import SunbeamClient
from abc import abstractmethod
from diagnostic_interface.config import command_settings


class SunbeamTab(DockerStackTab):
    def __init__(self):
        super().__init__()

        edit_btn = QPushButton("Edit Commands", self)
        edit_btn.clicked.connect(self.open_edit_dialog)

        # self.layout.addWidget(self.label)
        self.layout.addWidget(edit_btn)

    @staticmethod
    def open_edit_dialog():
        dlg = TextEditDialog(
            [command_settings.sunbeam_up_cmd, command_settings.sunbeam_down_cmd],
            ["Sunbeam Up", "Sunbeam Down"]
        )

        if dlg.exec_() == QDialog.Accepted:
            command_settings.sunbeam_up_cmd, command_settings.sunbeam_down_cmd = dlg.getText()

    @staticmethod
    def start_stack_command():
        return command_settings.sunbeam_up_cmd.split()

    @staticmethod
    def stop_stack_command():
        return command_settings.sunbeam_down_cmd.split()

    @property
    def project_directory(self):
        return settings.sunbeam_path

    def raise_docker_error(self):
        QMessageBox.critical(None, "Docker Error", f"Did not get a response from the Sunbeam Docker service "
                                                   f"stack.\n Is Docker running and is Sunbeam path correct? \n")

    @abstractmethod
    def evaluate_readiness(self, num_running_containers):
        client = SunbeamClient(settings.sunbeam_api_url)
        if num_running_containers == 6 and client.is_alive():
            self.status_label.setText("✅ Status: 100%")
            self.stack_running = True

        else:
            self.status_label.setText(f"❌ Status: {int(num_running_containers/7. * 100)}%")
            self.stack_running = True

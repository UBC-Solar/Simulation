from PyQt5.QtWidgets import QMessageBox
from diagnostic_interface import settings
from diagnostic_interface.tabs import DockerStackTab
from data_tools.query import SunbeamClient
from abc import abstractmethod


class SunbeamTab(DockerStackTab):
    def __init__(self):
        super().__init__()

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

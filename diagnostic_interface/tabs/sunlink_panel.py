from PyQt5.QtWidgets import QMessageBox
from diagnostic_interface import settings
from diagnostic_interface.tabs import DockerStackTab
from abc import abstractmethod


class SunlinkTab(DockerStackTab):
    def __init__(self):
        super().__init__()

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
            self.status_label.setText(f"❌ Status: {int(num_running_containers/4. * 100)}%")
            self.stack_running = True

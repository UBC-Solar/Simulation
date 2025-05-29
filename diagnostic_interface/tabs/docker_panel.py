import threading
import json

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import QTimer, Qt, QRunnable, QObject, pyqtSignal, QThreadPool
from diagnostic_interface.widgets import DockerLogWidget
import subprocess
from abc import abstractmethod


RESET = "\x1b[0m"
STATUS_POLLING_INTERVAL_MS = 1000
MAX_TEXT_LINES = 50


class UpdateStatusWorkerSignals(QObject):
    services = pyqtSignal(list)  # success or failure


class UpdateStatusWorker(QRunnable):
    def __init__(self, docker_stack: "DockerStackTab", cmd: list[str]):
        super().__init__()
        self.docker_stack = docker_stack
        self.cmd = cmd
        self.signals = UpdateStatusWorkerSignals()

    def run(self):
        try:
            result = subprocess.run(
                self.cmd,  # ["docker", "compose", "ps", "--format", "json"]
                cwd=self.docker_stack.project_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2,
                check=True,
            )

            output = result.stdout.strip()
            if output.startswith("["):
                services = json.loads(output)
            else:
                services = [json.loads(line) for line in output.splitlines() if line.strip()]

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            QTimer.singleShot(0, self.docker_stack.stop_timer)
            QTimer.singleShot(0, self.docker_stack.raise_docker_error)
            services = []

        self.signals.services.emit(services)


class DockerStackTab(QWidget):
    def __init__(self):
        super().__init__()
        self.stack_running = False
        self._thread_pool = QThreadPool()

        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.toggle_button = QPushButton("Start Stack")
        self.toggle_button.clicked.connect(self.toggle_stack)

        self.log_output = DockerLogWidget(self.start_stack_command)
        self.log_output.setReadOnly(True)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.toggle_button)
        self.layout.addWidget(self.log_output)
        self.setLayout(self.layout)

    @property
    @abstractmethod
    def project_directory(self):
        pass

    def _init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.do_update_status)
        self.timer.setInterval(STATUS_POLLING_INTERVAL_MS)

    @abstractmethod
    def raise_docker_error(self):
        pass

    def toggle_stack(self):
        if self.stack_running:
            self.stop_stack()
        else:
            self.start_stack()

    @staticmethod
    @abstractmethod
    def start_stack_command():
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def stop_stack_command():
        raise NotImplementedError

    def start_stack(self):
        def run():
            cmd = self.start_stack_command()
            subprocess.run(
                cmd,
                cwd=self.project_directory,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            QTimer.singleShot(0, self.do_update_status)

        threading.Thread(target=run, daemon=True).start()

    def stop_stack(self):
        def run():
            cmd = self.stop_stack_command()
            subprocess.run(
                cmd,
                cwd=self.project_directory,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            QTimer.singleShot(0, self.do_update_status)

        threading.Thread(target=run, daemon=True).start()

    def get_docker_status_cmd(self):
        start_cmd: list[str] = self.start_stack_command()

        cmd = " ".join(start_cmd)
        docker_cmd = cmd.replace("up -d", "ps --format json")

        return docker_cmd.split()

    def get_docker_logs_cmd(self):
        start_cmd: list[str] = self.start_stack_command()

        cmd = " ".join(start_cmd)
        docker_cmd = cmd.replace("up -d", "ps --format json")

        return docker_cmd.split()

    def do_update_status(self):
        # print(self.get_docker_status_cmd())
        worker = UpdateStatusWorker(self, self.get_docker_status_cmd())
        worker.signals.services.connect(self.update_status)
        self._thread_pool.start(worker)

    def update_status(self, services: list):
        if not services:
            self.stack_running = False
            self.status_label.setText("❌ Status: 0%")
            self.toggle_button.setText("Start Stack")
            self.log_output.clear()
            return

        states = [s["State"] for s in services]
        num_running_containers = len(list(["running" in s for s in states]))

        self.evaluate_readiness(num_running_containers)

        self.toggle_button.setText("Stop Stack")
        self.log_output.fetch_ansi_logs(self.project_directory)

    @abstractmethod
    def evaluate_readiness(self, num_running_containers: int):
        pass

    def stop_timer(self):
        self.timer.stop()

    def set_tab_active(self, active: bool):
        if active:
            QTimer.singleShot(0, self.do_update_status)
            self.timer.start()
        else:
            self.timer.stop()

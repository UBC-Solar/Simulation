import threading
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
import datetime
from diagnostic_interface import settings
from data_tools.query import SunbeamClient
import os
import pty
import subprocess
from PyQt5.QtWidgets import QTextEdit
from ansi2html import Ansi2HTMLConverter


RESET = "\x1b[0m"
STATUS_POLLING_INTERVAL_MS = 1000


class AnsiLogViewer(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAcceptRichText(True)
        self.setStyleSheet("QTextEdit { font-family: monospace; }")
        self.converter = Ansi2HTMLConverter(dark_bg=False, inline=True)

        self._last_log_time = datetime.datetime.now(datetime.UTC)

    def fetch_ansi_logs(self, project_dir: str):
        master_fd, slave_fd = pty.openpty()
        since_str = self._last_log_time.isoformat() + "Z"

        proc = subprocess.Popen(
            ["docker", "compose", "logs", "--since", since_str],
            cwd=project_dir,
            stdout=slave_fd,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "FORCE_COLOR": "1"},
        )
        self._last_log_time = datetime.datetime.utcnow()

        os.close(slave_fd)

        output = b""
        while True:
            try:
                chunk = os.read(master_fd, 1024)
                if not chunk:
                    break
                output += chunk
            except OSError:
                break

        os.close(master_fd)
        ansi_text = output.decode(errors="replace")

        lines = ansi_text.splitlines()
        for line in lines:
            if '\r' in line:
                line = line.split('\r')[-1]
                self._remove_last_line()
            html = self.converter.convert(RESET + line + RESET, full=False)
            self.insertHtml(html + "<br>")

        self._scroll_to_bottom()

    def _remove_last_line(self):
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()  # remove leftover newline

    def _scroll_to_bottom(self):
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def wheelEvent(self, event):
        # Disable mouse wheel scrolling
        pass

    def keyPressEvent(self, event):
        # Disable arrow key scrolling
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
            return
        super().keyPressEvent(event)


class DockerStackTab(QWidget):
    def __init__(self, ):
        super().__init__()
        self.stack_running = False
        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.toggle_button = QPushButton("Start Stack")
        self.toggle_button.clicked.connect(self.toggle_stack)

        self.log_output = AnsiLogViewer()
        self.log_output.setReadOnly(True)
        self._last_log_tail = ""
        self._max_lines = 50
        self._last_log_time = datetime.datetime.now(datetime.UTC)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def _init_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.setInterval(STATUS_POLLING_INTERVAL_MS)

    def toggle_stack(self):
        if self.stack_running:
            self.stop_stack()
        else:
            self.start_stack()

    def start_stack(self):
        def run():
            subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=settings.sunbeam_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            QTimer.singleShot(0, self.update_status)

        threading.Thread(target=run, daemon=True).start()

    def stop_stack(self):
        def run():
            subprocess.run(
                ["docker", "compose", "down"],
                cwd=settings.sunbeam_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            QTimer.singleShot(0, self.update_status)

        threading.Thread(target=run, daemon=True).start()

    def update_status(self):
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=settings.sunbeam_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=0.5,
                check=True,
            )

            output = result.stdout.strip()
            if output.startswith("["):
                services = json.loads(output)
            else:
                services = [json.loads(line) for line in output.splitlines() if line.strip()]

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            self.timer.stop()
            QMessageBox.critical(None, "Docker Error", f"Did not get a response from the Sunbeam Docker service stack.\n"
                                                       f"Is Docker running and is Sunbeam Path set? \n"
                                                       f"Additional Details: \n{str(e)}")

            services = None

        if not services:
            self.stack_running = False
            self.status_label.setText("❌ Status: 0%")
            self.toggle_button.setText("Start Stack")
            self.log_output.clear()
            return

        states = [s["State"] for s in services]
        num_running_containers = len(list(["running" in s for s in states]))

        client = SunbeamClient(settings.sunbeam_api_url)
        if num_running_containers == 6 and client.is_alive():
            self.status_label.setText("✅ Status: 100%")
            self.stack_running = True

        else:
            self.status_label.setText(f"❌ Status: {int(num_running_containers/7. * 100)}%")
            self.stack_running = True

        self.toggle_button.setText("Stop Stack")
        self.log_output.fetch_ansi_logs(settings.sunbeam_path)

    def set_tab_active(self, active: bool):
        if active:
            QTimer.singleShot(0, self.update_status)
            self.timer.start()
        else:
            self.timer.stop()

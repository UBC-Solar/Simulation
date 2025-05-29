from collections.abc import Callable

from PyQt5.QtCore import QProcess, QProcessEnvironment, Qt
from PyQt5.QtWidgets import QTextEdit
import datetime
from ansi2html import Ansi2HTMLConverter


RESET = "\x1b[0m"


class DockerLogWidget(QTextEdit):
    def __init__(self, start_stack_command: Callable[[], list[str]]):
        super().__init__()
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.converter = Ansi2HTMLConverter(dark_bg=False, inline=True)
        self._last_log_time = datetime.datetime.utcnow()
        self._start_stack_command = start_stack_command

        # --- set up the QProcess once ---
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)

    def get_docker_logs_cmd(self, replace_str: str) -> list[str]:
        start_cmd: list[str] = self._start_stack_command()

        cmd = " ".join(start_cmd)
        docker_cmd = cmd.replace("up -d", replace_str)

        return docker_cmd.split()

    def fetch_ansi_logs(self, project_dir: str):
        # 1) compute the “since” timestamp
        since_str = self._last_log_time.isoformat() + "Z"
        self._last_log_time = datetime.datetime.utcnow()

        # 2) set up environment so Docker still emits color
        env = QProcessEnvironment.systemEnvironment()
        env.insert("FORCE_COLOR", "1")
        self._proc.setProcessEnvironment(env)

        # Get command
        cmd = self.get_docker_logs_cmd(f"logs --since {since_str}")

        # 3) set working dir and launch
        self._proc.setWorkingDirectory(project_dir)
        self._proc.start(
            cmd[0], cmd[1:]
        )

    def _on_ready_read(self):
        # read whatever’s arrived so far
        raw = self._proc.readAllStandardOutput()
        text = bytes(raw).decode(errors="replace")

        for part in text.splitlines():
            # handle “\r” style overwrites
            if "\r" in part:
                part = part.rsplit("\r", 1)[-1]
                self._remove_last_line()
            html = self.converter.convert(RESET + part + RESET, full=False)
            self.insertHtml(html + "<br>")

        self._scroll_to_bottom()

    def _remove_last_line(self):
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()

    def _scroll_to_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    # disable wheel/key scrolling:
    def wheelEvent(self, event):    pass
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
            return
        super().keyPressEvent(event)

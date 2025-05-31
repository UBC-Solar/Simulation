from collections.abc import Callable
from PyQt5.QtCore import QProcess, QProcessEnvironment, Qt
from PyQt5.QtWidgets import QTextEdit
import datetime
import os


class DockerLogWidget(QTextEdit):
    """A QTextEdit that fetches Docker logs incrementally and truncates old entries."""
    def __init__(self, start_stack_command: Callable[[], str], max_lines: int = 1000):
        super().__init__()
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.max_lines = max_lines
        self._last_log_time = datetime.datetime.utcnow()
        self._start_stack_command = start_stack_command

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)

    def get_docker_logs_cmd(self, replace_str: str) -> str:
        base_cmd_str = self._start_stack_command()
        return base_cmd_str.replace("up -d", replace_str)

    def fetch_logs(self, project_dir: str):
        # compute "since" timestamp
        since = self._last_log_time.isoformat() + "Z"
        self._last_log_time = datetime.datetime.utcnow()

        # ensure Docker emits color-free output
        env = QProcessEnvironment.systemEnvironment()
        env.insert("FORCE_COLOR", "0")
        self._proc.setProcessEnvironment(env)

        docker_cmd_str = self.get_docker_logs_cmd(f"logs --since {since}")
        if not docker_cmd_str.strip():
            return

        # 4) Depending on platform, run via an appropriate shell
        #    - On Unix/macOS: use 'bash -lc "<docker_cmd_str>"'
        #    - On Windows: use 'cmd /C "<docker_cmd_str>"'
        if os.name == "nt":
            # Windows
            shell_prog = "cmd"
            shell_args = ["/C", docker_cmd_str]
        else:
            # Unix-like; assumes bash is available
            shell_prog = "bash"
            shell_args = ["-lc", docker_cmd_str]

        self._proc.setWorkingDirectory(project_dir)
        self._proc.start(shell_prog, shell_args)

    def _on_ready_read(self):
        raw = self._proc.readAllStandardOutput()
        text = bytes(raw).decode("utf-8", errors="replace")
        lines = text.splitlines()

        cursor = self.textCursor()
        cursor.beginEditBlock()
        self.setUpdatesEnabled(False)

        for line in lines:
            if "\r" in line:
                # spinner/carriage-return style overwrite
                line = line.rsplit("\r", 1)[-1]
                self._remove_last_line()
            cursor.insertText(line + "\n")

        cursor.endEditBlock()
        self.setUpdatesEnabled(True)

        self._prune_old_lines()
        self._scroll_to_bottom()

    def _prune_old_lines(self):
        doc = self.document()
        overflow = doc.blockCount() - self.max_lines
        if overflow > 0:
            block = doc.findBlockByNumber(overflow)
            cursor = self.textCursor()
            cursor.setPosition(0)
            cursor.setPosition(block.position(), cursor.KeepAnchor)
            cursor.removeSelectedText()

    def _remove_last_line(self):
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()

    def _scroll_to_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    # disable wheel scrolling
    def wheelEvent(self, event):
        pass

    # disable arrow/page key scrolling
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
            return
        super().keyPressEvent(event)

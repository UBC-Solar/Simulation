from PyQt5.QtCore import Qt
import datetime
import os
import pty
import subprocess
from PyQt5.QtWidgets import QTextEdit
from ansi2html import Ansi2HTMLConverter


RESET = "\x1b[0m"


class DockerLogWidget(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAcceptRichText(True)
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
        cursor.deletePreviousChar()

    def _scroll_to_bottom(self):
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def wheelEvent(self, event):
        pass

    def keyPressEvent(self, event):
        # Disable arrow key scrolling
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
            return
        super().keyPressEvent(event)

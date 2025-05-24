import re
from PyQt5.QtCore import Qt, pyqtSignal, QProcess, QByteArray
from PyQt5.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QPushButton
from ansi2html import Ansi2HTMLConverter

RESET = "\x1b[0m"


class CommandOutputWidget(QTextEdit):
    """A QTextEdit that runs a command in a QProcess and renders ANSI output (incl. spinners)."""
    # emitted whenever new raw text arrives
    _chunk_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # ANSI → HTML converter
        self._converter = Ansi2HTMLConverter(dark_bg=False, inline=True)

        # Qt process for running the command
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)

        # connect to our own slot to update UI in main thread
        self._chunk_ready.connect(self._append_chunk)

    def start_command(self, program: str, args: list[str]=(), cwd: str=None, env: dict=None):
        """Launches the given program+args."""
        self.clear()
        if cwd:
            self._proc.setWorkingDirectory(cwd)
        if env:
            qt_env = self._proc.processEnvironment()
            for k, v in env.items():
                qt_env.insert(k, v)
            self._proc.setProcessEnvironment(qt_env)

        # ensure apps that detect a TTY will emit color
        self._proc.start(program, args)

    def stop(self):
        """Terminate the process."""
        self._proc.terminate()

    def _on_ready_read(self):
        """Read raw bytes from the process and emit decoded text."""
        raw: QByteArray = self._proc.readAllStandardOutput()
        text = bytes(raw).decode("utf-8", errors="replace")
        self._chunk_ready.emit(text)

    def _append_chunk(self, text: str):
        """
        Turn the incoming text into HTML, handling:
         - '\r' (carriage-return) to overwrite the last line (for spinners)
         - '\n' or '\r\n' → new line
         - other text → ANSI→HTML conversion
        """
        # Split on any combination of \r and \n, but keep them in the list
        parts = re.split(r'(\r\n|\r|\n)', text)

        for part in parts:
            if part == "\r":
                # remove the last rendered line so we can overwrite it
                self._remove_last_line()
            elif part in ("\n", "\r\n"):
                # explicit newline
                self.insertHtml("<br>")
            else:
                # regular text: convert ANSI codes → HTML
                html = self._converter.convert(RESET + part + RESET, full=False)
                # insert without an extra <br> so that we only break on newline tokens
                self.insertHtml(html)

        self._scroll_to_bottom()

    def _remove_last_line(self):
        """Delete the last block (line) in the QTextEdit."""
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()

    def _scroll_to_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    # disable wheel scrolling if you like
    def wheelEvent(self, ev):
        pass

    def keyPressEvent(self, ev):
        # disable up/down arrow scrolling
        if ev.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
            return
        super().keyPressEvent(ev)

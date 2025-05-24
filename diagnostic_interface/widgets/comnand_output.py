import re
from PyQt5.QtCore import Qt, pyqtSignal, QProcess, QByteArray
from PyQt5.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QPushButton, QMessageBox
from ansi2html import Ansi2HTMLConverter
import os
import shlex

RESET = "\x1b[0m"


class CommandOutputWidget(QTextEdit):
    """A QTextEdit that runs a command in a QProcess and renders ANSI output (incl. spinners)."""
    _chunk_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._converter = Ansi2HTMLConverter(dark_bg=False, inline=True)
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)
        self._chunk_ready.connect(self._append_chunk)

    def start_in_venv(
            self,
            project_root: str,
            script_path: str,
            args: list[str] = None,
            venv_subdir: str = "environment",
    ):
        """
        Activate the venv and run a Python script.

        :param project_root: Path to your project root
        :param script_path: Path (relative to project_root) of the .py you want to run
        :param args: List of args to pass to the script
        :param venv_subdir: Name of the venv folder under project_root (default "venv")
        """
        args = args or []

        # full paths
        activate = os.path.join(project_root, venv_subdir, "bin", "activate")
        script = os.path.join(project_root, script_path)

        # safely shell-quote everything
        quoted_activate = shlex.quote(activate)
        quoted_script = shlex.quote(script)
        quoted_args = " ".join(shlex.quote(a) for a in args)

        # build the bash -lc command
        cmd = (
                f"source {quoted_activate} && "
                f"exec python {quoted_script}"
                + (f" {quoted_args}" if quoted_args else "")
        )

        # set working dir so relative imports, file writes, etc. use project_root
        self._proc.setWorkingDirectory(project_root)
        # kick off bash -lc "source ... && exec python ..."
        self._proc.start("bash", ["-lc", cmd])

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

        lines = text.splitlines()
        if lines:
            last = lines[-1]
            if re.search(r"\(y/N\)\s*>\s*$", last):
                # strip the trailing prompt marker for nicer display
                prompt = re.sub(r"\s*\(y/N\)\s*>\s*$", "(y/N)", last)
                self._ask_and_respond(prompt)

    def _ask_and_respond(self, prompt_text: str):
        """Show a QMessageBox for the prompt, then write back to the process."""
        answer = QMessageBox.question(
            self,
            "Confirmation Required",
            prompt_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        resp = ("y\n" if answer == QMessageBox.Yes else "n\n").encode("utf-8")
        self._proc.write(resp)

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

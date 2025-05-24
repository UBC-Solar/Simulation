import re
from PyQt5.QtCore import Qt, pyqtSignal, QProcess
from PyQt5.QtWidgets import QTextEdit, QMessageBox
from ansi2html import Ansi2HTMLConverter
import os
import shlex
import sys

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
        Activate the venv under `project_root/venv_subdir`, then exec:
            python {script_path} {args...}
        in a PTY so spinners (save/restore ANSI) work.
        """
        args = args or []

        activate = os.path.join(project_root, venv_subdir, "bin", "activate")
        script = os.path.join(project_root, script_path)
        qa = shlex.quote(activate)
        qs = shlex.quote(script)
        qargs = " ".join(shlex.quote(a) for a in args)

        # the “inner” command we want to run under PTY
        inner = f"source {qa} && exec python {qs}" + (f" {qargs}" if qargs else "")

        if sys.platform.startswith("linux"):
            wrapper = f"script -q -e -c {shlex.quote(inner)} /dev/null"
        else:
            # on macOS (BSD script) there's no -c, so pass the command as args
            #  -q: quiet, no start/end messages
            #  -e: return child exit code (BSD supports -e)
            #  file: /dev/null
            #  command...: bash -lc inner
            wrapper = f"script -q -e /dev/null bash -lc {shlex.quote(inner)}"

        self._proc.setWorkingDirectory(project_root)
        self._proc.start("bash", ["-lc", wrapper])

    def stop(self):
        """Terminate the process."""
        self._proc.terminate()

    def _on_ready_read(self):
        raw = self._proc.readAllStandardOutput()
        text = bytes(raw).decode("utf-8", errors="replace")
        self._chunk_ready.emit(text)

    def _append_chunk(self, text: str):
        # 1) Convert ANSI save/restore → '\r' (and drop restore)
        text = re.sub(r'\x1b7|\x1b\[s', '\r', text)
        text = re.sub(r'\x1b8|\x1b\[u', '', text)

        # 2) Split on CR/LF and render ANSI → HTML
        parts = re.split(r"(\r\n|\r|\n)", text)
        for part in parts:
            if part == "\r":
                self._remove_last_line()
            elif part in ("\n", "\r\n"):
                self.insertHtml("<br>")
            else:
                html = self._converter.convert(RESET + part + RESET, full=False)
                self.insertHtml(html)

        self._scroll_to_bottom()

        # 3) If the last line is exactly "(y/N) >", prompt the user
        lines = text.splitlines()
        if lines and re.search(r"\(y/N\)\s*>\s*$", lines[-1]):
            prompt = re.sub(r"\s*\(y/N\)\s*>\s*$", "(y/N)", lines[-1])
            self._ask_and_respond(prompt)

    def _ask_and_respond(self, prompt_text: str):
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

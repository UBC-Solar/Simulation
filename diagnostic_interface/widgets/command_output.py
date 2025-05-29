import re
from PyQt5.QtCore import Qt, pyqtSignal, QProcess
from PyQt5.QtWidgets import QTextEdit, QMessageBox
from PyQt5.QtGui import QTextCursor
from ansi2html import Ansi2HTMLConverter
from typing import Callable
import shlex

RESET = "\x1b[0m"


class CommandOutputWidget(QTextEdit):
    """A QTextEdit that runs a command in a QProcess and renders ANSI output (incl. spinners)."""
    _chunk_ready = pyqtSignal(str)

    def __init__(self, parent=None, max_lines=10):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.max_lines = max_lines

        self._active = False

        self._converter = Ansi2HTMLConverter(dark_bg=False, inline=True)
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)
        self._chunk_ready.connect(self._append_chunk)

    def deactivate(self):
        self._active = False

    def activate(self):
        self._active = True

    def start_cmd(self, cmd: str):
        start_cmd = shlex.split(cmd)

        self._proc.start(start_cmd[0], start_cmd[1:])

    def stop(self):
        """Terminate the process."""
        self._proc.terminate()

    def _on_ready_read(self):
        if self._active:
            raw = self._proc.readAllStandardOutput()
            text = bytes(raw).decode("utf-8", errors="replace")
            self._chunk_ready.emit(text)

    def _append_chunk(self, text: str):
        # 1) Convert ANSI → '\r' as you already do…
        text = re.sub(r'\x1b7|\x1b\[s', '\r', text)
        text = re.sub(r'\x1b8|\x1b\[u', '', text)

        # 2) Split into parts
        parts = re.split(r"(\r\n|\r|\n)", text)

        # 3) Batch insert
        cursor = self.textCursor()
        cursor.beginEditBlock()
        # disable repaint until done
        self.setUpdatesEnabled(False)

        for part in parts:
            if part == "\r":
                # handle carriage-return by pruning old lines below
                self._remove_last_line()
            elif part in ("\n", "\r\n"):
                cursor.insertHtml("<br>")
            else:
                html = self._converter.convert(RESET + part + RESET, full=False)
                cursor.insertHtml(html)

        cursor.endEditBlock()
        self.setUpdatesEnabled(True)

        # 4) prune any overflow in one shot
        self._prune_old_blocks()

        # 5) scroll
        self._scroll_to_bottom()

        # 3) If the last line is exactly "(y/N) >", prompt the user
        lines = text.splitlines()
        if lines and re.search(r"\(y/N\)\s*>\s*$", lines[-1]):
            prompt = re.sub(r"\s*\(y/N\)\s*>\s*$", "(y/N)", lines[-1])
            self._ask_and_respond(prompt)

    def _prune_old_blocks(self):
        doc = self.document()
        overflow = doc.blockCount() - self.max_lines
        if overflow <= 0:
            return

        # find the position at the start of the first-kept block
        first_kept = doc.findBlockByNumber(overflow)
        to = first_kept.position()

        # delete from document start up to `to`
        c = QTextCursor(doc)
        c.setPosition(0)
        c.setPosition(to, QTextCursor.KeepAnchor)
        c.removeSelectedText()


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

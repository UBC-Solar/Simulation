import re
import shlex
from PyQt5.QtCore import Qt, pyqtSignal, QProcess
from PyQt5.QtWidgets import QTextEdit, QMessageBox


class CommandOutputWidget(QTextEdit):
    """A QTextEdit that runs a command in a QProcess and renders ANSI output (incl. spinners)."""
    _chunk_ready = pyqtSignal(str)

    def __init__(self, parent=None, max_lines=10):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.max_lines = max_lines

        self._active = False

        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_ready_read)
        self._chunk_ready.connect(self._append_chunk)

    def deactivate(self):
        self._active = False

    def activate(self):
        self._active = True

    def start_cmd(self, cmd: str):
        args = shlex.split(cmd)
        if args:
            self._proc.start(args[0], args[1:])

    def stop(self):
        """Terminate the process."""
        self._proc.terminate()

    def _on_ready_read(self):
        if self._active:
            raw = self._proc.readAllStandardOutput()
            text = bytes(raw).decode("utf-8", errors="replace")
            self._chunk_ready.emit(text)

    def _append_chunk(self, text: str):
        # Normalize spinner resets and restores to carriage returns
        text = re.sub(r'\x1b7|\x1b\[s', '\r', text)
        text = re.sub(r'\x1b8|\x1b\[u', '', text)

        parts = re.split(r'(\r\n|\r|\n)', text)
        cursor = self.textCursor()
        cursor.beginEditBlock()
        self.setUpdatesEnabled(False)

        for part in parts:
            if part == '\r':
                # Remove the previous line for spinner animation
                self._remove_last_line()
            else:
                cursor.insertText(part)

        cursor.endEditBlock()
        self.setUpdatesEnabled(True)

        self._prune_old_lines()
        self._scroll_to_bottom()

        # Handle confirmation prompts ending with '(y/N) >'
        if text.rstrip().endswith('(y/N) >'):
            self._ask_and_respond('(y/N)')

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

    def _ask_and_respond(self, prompt: str):
        answer = QMessageBox.question(
            self,
            "Confirmation Required",
            prompt,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        resp = ("y\n" if answer == QMessageBox.Yes else "n\n").encode('utf-8')
        self._proc.write(resp)

    def _scroll_to_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    # Disable wheel scrolling
    def wheelEvent(self, ev):
        pass

    # Disable arrow/page scrolling
    def keyPressEvent(self, ev):
        if ev.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
            return
        super().keyPressEvent(ev)

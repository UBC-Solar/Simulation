import subprocess
from collections.abc import Callable
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextEdit
import datetime
import os
import shlex


class DockerLogWidget(QTextEdit):
    """
    A QTextEdit that synchronously fetches Docker logs in batches (via subprocess.run),
    prunes old lines, and handles carriage-return “spinner” overwrites.

    - `start_stack_command: Callable[[], str]` should return a single, fully-formed
      command string (e.g. "docker-compose -f docker-compose.yml up -d"). We will
      replace "up -d" with "logs --since <timestamp>Z" each time we fetch.
    - `max_lines` is the total number of text lines to keep before pruning older lines.

    NOTE: Because we use `subprocess.run(..., shell=True)` directly, **fetch_logs() will
    block the GUI thread until the external command completes**. If you need non-blocking
    behavior, move `fetch_logs()` into a worker thread.
    """

    def __init__(self, start_stack_command: Callable[[], str], max_lines: int = 1000):
        super().__init__()
        self.setReadOnly(True)
        # We only insert plain text, so rich text is disabled.
        self.setAcceptRichText(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.max_lines = max_lines
        self._last_log_time = datetime.datetime.utcnow()
        self._start_stack_command = start_stack_command

    def _build_logs_command_str(self, since_iso: str) -> str:
        """
        1) Call start_stack_command() to get the base `up -d` invocation (single string).
        2) Replace "up -d" with "logs --since <since_iso>Z".
           e.g.  base = "docker-compose -f docker-compose.yml up -d"
                 since_iso = "2025-05-30T16:00:00", we return
                 "docker-compose -f docker-compose.yml logs --since 2025-05-30T16:00:00Z"
        """
        base_cmd = self._start_stack_command()
        if not isinstance(base_cmd, str) or not base_cmd.strip():
            raise ValueError("start_stack_command() must return a non-empty command string.")
        return base_cmd.replace("up -d", f"logs --since {since_iso}Z")

    def fetch_logs(self, project_dir: str):
        """
        Fetch new logs since the last timestamp. This method *blocks* until
        the `docker logs --since <timestamp>` process exits, then updates the widget.
        """
        # 1) Compute ISO‐formatted "since" timestamp (UTC)
        since_iso = self._last_log_time.replace(microsecond=0).isoformat()
        self._last_log_time = datetime.datetime.utcnow()

        # 2) Build the Docker logs command string
        docker_cmd_str = self._build_logs_command_str(since_iso)
        if not docker_cmd_str.strip():
            return  # nothing to do if the string is empty

        # 3) Ensure no ANSI colors are emitted
        env = os.environ.copy()
        env["FORCE_COLOR"] = "0"

        # 4) Decide which shell wrapper to use
        if os.name == "nt":
            # On Windows: wrap in cmd /C "<...>"
            shell_cmd = f'cmd /C "{docker_cmd_str}"'
        else:
            # On Unix/macOS: wrap in bash -lc "<...>"
            # We do NOT shlex.quote(docker_cmd_str) here, because we want the entire
            # string passed verbatim within the quotes.
            shell_cmd = f'bash -lc "{docker_cmd_str}"'

        # 5) Run synchronously (this will block until completion)
        try:
            completed = subprocess.run(
                shell_cmd,
                shell=True,
                cwd=project_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as e:
            # If the call fails entirely (e.g. command not found), append the error and return.
            self._append_text(f"[Error running logs command]: {e}\n")
            return

        # 6) Process stdout lines
        stdout_text = completed.stdout or ""
        lines = stdout_text.splitlines()

        # 7) Insert lines into the QTextEdit (handling '\r' overwrites)
        cursor = self.textCursor()
        cursor.beginEditBlock()
        self.setUpdatesEnabled(False)

        for raw_line in lines:
            # If carriage-return is present, remove everything up to the last '\r',
            # then delete the previous line in the widget before inserting the new text.
            if "\r" in raw_line:
                new_line = raw_line.rsplit("\r", 1)[-1]
                self._remove_last_line()
            else:
                new_line = raw_line

            cursor.insertText(new_line + "\n")

        cursor.endEditBlock()
        self.setUpdatesEnabled(True)

        # 8) Prune old lines if we've exceeded max_lines
        self._prune_old_lines()

        # 9) Scroll to bottom so the newest logs are visible
        self._scroll_to_bottom()

    def _prune_old_lines(self):
        """Delete the oldest blocks if blockCount() exceeds max_lines."""
        doc = self.document()
        overflow = doc.blockCount() - self.max_lines
        if overflow > 0:
            block_to_keep = doc.findBlockByNumber(overflow)
            cur = self.textCursor()
            cur.setPosition(0)
            cur.setPosition(block_to_keep.position(), cur.KeepAnchor)
            cur.removeSelectedText()

    def _remove_last_line(self):
        """
        Delete the last QTextBlock (line) in the widget. Used for spinner overwrites.
        """
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.BlockUnderCursor)
        cursor.removeSelectedText()
        # After removing text of that block, remove the trailing newline (if any)
        cursor.deletePreviousChar()

    def _scroll_to_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())

    # Prevent the user from scrolling with wheel or arrow keys:
    def wheelEvent(self, event):
        pass

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown):
            return
        super().keyPressEvent(event)

    def _append_text(self, text: str):
        """
        Helper to insert arbitrary text (e.g. error messages) at the bottom,
        then prune & scroll appropriately.
        """
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        self._prune_old_lines()
        self._scroll_to_bottom()

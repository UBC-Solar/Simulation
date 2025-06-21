from PyQt5.QtWidgets import (
    QVBoxLayout,
    QDialog, QLineEdit, QFormLayout,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt


class TextEditDialog(QDialog):
    def __init__(self, current_commands: list[str], command_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Command")
        self.layout = QFormLayout()
        self.lines = []

        for command, command_name in zip(current_commands, command_names):
            # --- Line edit + reset button ---
            newQLineEdit = QLineEdit()
            newQLineEdit.setMinimumSize(400, 100)
            newQLineEdit.setText(command)

            self.lines.append(newQLineEdit)

            self.layout.addRow(f"{command_name}: ", newQLineEdit)

        # --- OK / Cancel buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # --- Layout everything ---
        vbox = QVBoxLayout(self)
        vbox.addLayout(self.layout)
        vbox.addWidget(buttons)

    def getText(self) -> list[str]:
        """Return whatever is currently in the line edit."""
        return [line.text() for line in self.lines]

from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QSpinBox, QLineEdit, QFormLayout, QFileDialog,
                             QToolButton, QHBoxLayout, QMessageBox, QFrame, QWidget, QLabel, QVBoxLayout
                             )
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import Qt
import os
from typing import Callable


class PathFrame(QFrame):
    def __init__(self, current_path: str):
        super().__init__()

        self._path_label = QLabel()
        self._path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # Elide long path
        font_metrics = QFontMetrics(self._path_label.font())
        elided = font_metrics.elidedText(current_path, Qt.ElideLeft, 200)
        self._path_label.setText(elided)
        self._path_label.setToolTip(current_path)

        # QFrame to create a visible box
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        self.setLineWidth(2)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self._path_label)
        self.layout().setContentsMargins(2, 2, 2, 2)

    @property
    def path_label(self):
        return self._path_label


class PathSelectionBox(QWidget):
    def __init__(self, current_path: str, button_callback: Callable[[], None]):
        super().__init__()

        self._frame = PathFrame(current_path)

        self._browse_button = QToolButton()
        font = self._browse_button.font()
        font.setPointSize(14)
        self._browse_button.setFont(font)
        self._browse_button.setText("📁")
        self._browse_button.setFixedWidth(32)
        self._browse_button.clicked.connect(button_callback)

        hbox = QHBoxLayout()
        hbox.addWidget(self._frame)
        hbox.addWidget(self._browse_button)
        hbox.setContentsMargins(0, 0, 0, 0)

        self.setLayout(hbox)

    @property
    def frame(self):
        return self._frame


class SettingsDialog(QDialog):
    def __init__(
            self,
            current_interval: int,
            current_client_address: str,
            current_sunbeam_path: str,
            current_sunlink_path: str,
            parent=None
    ):
        """
        :param int current_interval: the current interval that is set on our timer.
        :param str current_client_address: the URL from where we are currently querying data.
        :param str current_sunbeam_path: the current Sunbeam path
        """
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 200)

        layout = QFormLayout()

        # Refresh interval selector
        self._interval_spinbox = QSpinBox()
        self._interval_spinbox.setValue(current_interval)  # convert ms to s
        layout.addRow("Plot Refresh Interval:", self._interval_spinbox)

        # Client selector
        self._client_input = QLineEdit()
        self._client_input.setText(current_client_address)
        layout.addRow("Sunbeam API URL:", self._client_input)

        self._selected_sunlink_path = current_sunlink_path
        self._sunlink_path_widget = PathSelectionBox(current_sunlink_path, self.select_sunlink_folder)
        layout.addRow("Sunlink Path:", self._sunlink_path_widget)

        self._selected_sunbeam_path = current_sunbeam_path
        self._sunbeam_path_widget = PathSelectionBox(current_sunbeam_path, self.select_sunbeam_folder)
        layout.addRow("Sunbeam Path:", self._sunbeam_path_widget)

        # OK/Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _select_docker_folder(self, attr_name: str, widget_attr: str) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder with docker-compose.yaml")

        if folder:
            if any(os.path.isfile(os.path.join(folder, f)) for f in ["docker-compose.yaml", "docker-compose.yml"]):
                setattr(self, attr_name, folder)
                widget = getattr(self, widget_attr)
                widget.frame.path_label.setText(folder)
                widget.frame.path_label.setToolTip(folder)
            else:
                QMessageBox.warning(self, "Warning", "Please select a folder with docker-compose.yaml!")

    def select_sunlink_folder(self):
        self._select_docker_folder("_selected_sunlink_path", "_sunlink_path_widget")

    def select_sunbeam_folder(self):
        self._select_docker_folder("_selected_sunbeam_path", "_sunbeam_path_widget")

    def get_settings(self) -> tuple[int, str, str, str]:
        return (
            self._interval_spinbox.value(),
            self._client_input.text(),
            self._selected_sunbeam_path,
            self._selected_sunlink_path
        )

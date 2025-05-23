from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QSpinBox, QLineEdit, QFormLayout, QFileDialog,
                             QToolButton, QHBoxLayout, QMessageBox, QFrame, QWidget, QLabel, QVBoxLayout
                             )
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtCore import Qt
import os


class SettingsDialog(QDialog):
    def __init__(self, current_interval, current_client_address, current_sunbeam_path, parent=None):
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
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setValue(current_interval)  # convert ms to s
        layout.addRow("Plot Refresh Interval:", self.interval_spinbox)

        # Client selector
        self.client_input = QLineEdit()
        self.client_input.setText(current_client_address)
        layout.addRow("Sunbeam API URL:", self.client_input)

        self.selected_sunbeam_path = current_sunbeam_path
        # QLabel for path text
        self.sunbeam_path_label = QLabel()
        self.sunbeam_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # Elide long path
        font_metrics = QFontMetrics(self.sunbeam_path_label.font())
        elided = font_metrics.elidedText(self.selected_sunbeam_path, Qt.ElideLeft, 200)
        self.sunbeam_path_label.setText(elided)
        self.sunbeam_path_label.setToolTip(self.selected_sunbeam_path)

        # QFrame to create a visible box
        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Sunken)
        self.frame.setLineWidth(2)
        self.frame.setLayout(QVBoxLayout())
        self.frame.layout().addWidget(self.sunbeam_path_label)
        self.frame.layout().setContentsMargins(2, 2, 2, 2)

        self.browse_button = QToolButton()
        font = self.browse_button.font()
        font.setPointSize(14)
        self.browse_button.setFont(font)
        self.browse_button.setText("📁")
        self.browse_button.setFixedWidth(32)
        self.browse_button.clicked.connect(self.select_folder)

        hbox = QHBoxLayout()
        hbox.addWidget(self.frame)
        hbox.addWidget(self.browse_button)
        hbox.setContentsMargins(0, 0, 0, 0)

        path_widget = QWidget()
        path_widget.setLayout(hbox)
        layout.addRow("Sunbeam Path:", path_widget)

        # OK/Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder with docker-compose.yaml")

        if folder:
            if any(os.path.isfile(os.path.join(folder, f)) for f in ["docker-compose.yaml", "docker-compose.yml"]):
                self.selected_sunbeam_path = folder
                self.sunbeam_path_label.setText(self.selected_sunbeam_path)
                self.sunbeam_path_label.setToolTip(self.selected_sunbeam_path)

            else:
                QMessageBox.warning(self, "Warning", "Please select a folder with docker-compose.yaml!")

    def get_settings(self):
        return self.interval_spinbox.value(), self.client_input.text(), self.selected_sunbeam_path

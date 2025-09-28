from typing import Optional
from prescriptive_interface import SimulationCanvas, SpeedPlotCanvas
from micro_strategy import run_micro_simulation
from pathlib import Path
import io
import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QSizePolicy, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView


class SimulationTab(QWidget):
    def __init__(self):
        """
        Initialize the SimulationTab widget.

        Sets up internal references and prepares the UI layout for running simulations.
        A callback function is required to handle the simulation logic when the run button is pressed.

        :param run_callback: Function to be called when the simulation run button is clicked.
        :type run_callback: Callable
        :returns: None
        :rtype: None
        """
        super().__init__()
        self.start_button: Optional[QPushButton] = None
        self.sim_output_text: Optional[QTextEdit] = None
        self.sim_canvas: Optional[SimulationCanvas] = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # self.start_button = QPushButton("Run Simulation")
        # self.start_button.clicked.connect(self.run_callback)
        # layout.addWidget(self.start_button)

        self.sim_output_text = QTextEdit()
        self.sim_output_text.setReadOnly(True)
        self.sim_output_text.setFixedHeight(100)
        layout.addWidget(self.sim_output_text)

        self.sim_canvas = SimulationCanvas()
        layout.addWidget(self.sim_canvas)

        self.setLayout(layout)


class OptimizationTab(QWidget):
    def __init__(self, optimize_callback, lap_callback, settings_callback):
        """
        Initialize the OptimizationTab widget.

        Sets up internal UI components for running the simulation optimization and navigating lap segments.
        Requires two callback functions to be passed in for optimization logic and lap navigation.

        :param optimize_callback: Function to be called when the optimization button is clicked.
        :type optimize_callback: Callable
        :param lap_callback: Function to be called when lap navigation buttons are clicked.
        :type lap_callback: Callable
        :returns: None
        :rtype: None
        """
        super().__init__()
        self.optimize_callback = optimize_callback
        self.settings_callback = settings_callback
        # self.lap_callback = lap_callback

        self.optimize_button: Optional[QPushButton] = None
        self.output_text: Optional[QTextEdit] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.speed_canvas: Optional[SpeedPlotCanvas] = None
        self.settings_button: Optional[QPushButton] = None
        self.prev_lap_button: Optional[QPushButton] = None
        self.next_lap_button: Optional[QPushButton] = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.optimize_button = QPushButton("Optimize Simulation")
        self.optimize_button.clicked.connect(self.optimize_callback)
        layout.addWidget(self.optimize_button)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.speed_canvas = SpeedPlotCanvas(self)
        self.speed_canvas.setMinimumHeight(500)
        self.speed_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.speed_canvas)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.settings_callback)

        nav_layout = QVBoxLayout()
        nav_layout.addWidget(self.settings_button)
        layout.addLayout(nav_layout)

        self.setLayout(layout)


class WorkerThread(QThread):
    output_signal = pyqtSignal(str)
    error_signal  = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def run(self):
        """This method is called in the new thread."""
        buffer = io.StringIO()
        try:
            # Redirect print() and exceptions into buffer
            sys_stdout, sys_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = buffer, buffer

            run_micro_simulation.main()
            text = buffer.getvalue().strip()
            self.output_signal.emit(text or "Script completed successfully.")

        except Exception as e:
            # Emit the exception text
            self.error_signal.emit(f"Error running script: {e}")

        finally:
            # restore
            sys.stdout, sys.stderr = sys_stdout, sys_stderr
            self.finished_signal.emit()


class HtmlViewerTab(QWidget):
    """A tab that displays an HTML file and runs a fixed script in a QThread."""

    def __init__(self, html_path: str):
        super().__init__()
        self.html_path = html_path

        self.view = None
        self.run_button = None
        self.sim_output_text = None
        self.worker = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.run_button = QPushButton("Run Report Generator")
        self.run_button.clicked.connect(self.on_run_clicked)
        layout.addWidget(self.run_button)

        self.sim_output_text = QTextEdit()
        self.sim_output_text.setReadOnly(True)
        self.sim_output_text.setFixedHeight(100)
        layout.addWidget(self.sim_output_text)

        self.view = QWebEngineView()
        local_url = QUrl.fromLocalFile(str(Path(self.html_path).resolve()))
        self.view.load(local_url)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.view)

    def on_run_clicked(self):
        self.run_button.setEnabled(False)
        self.sim_output_text.clear()

        # create the worker thread
        self.worker = WorkerThread(self)
        self.worker.output_signal.connect(self.sim_output_text.append)
        self.worker.error_signal.connect(self.sim_output_text.append)
        self.worker.finished_signal.connect(self.on_worker_finished)

        self.worker.start()

    def on_worker_finished(self):
        """Called in the main thread when the worker is done."""
        self.reload()
        self.run_button.setEnabled(True)

    def reload(self):
        """Reload the HTML view."""
        if self.view:
            self.view.reload()

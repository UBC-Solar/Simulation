from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTextEdit, QProgressBar, QSizePolicy
)
from prescriptive_interface import SimulationCanvas, SpeedPlotCanvas


class SimulationTab(QWidget):
    def __init__(self, run_callback):
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
        self.run_callback = run_callback
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

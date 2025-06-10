import pathlib

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QTabWidget,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from data_tools import SunbeamClient
from diagnostic_interface.widgets import DataSelect
from diagnostic_interface.tabs import SunbeamTab, SunlinkTab, PlotTab, UpdatableTab, TelemetryTab, SOCTab, PowerTab
from diagnostic_interface.dialog import SettingsDialog
from diagnostic_interface import settings


# Interface aesthetic parameters
WINDOW_TITLE = "Diagnostic Interface"
X_COORD = 100  # Sets the x-coord where the interface will be created
Y_COORD = 100  # Sets the y-coord where the interface will be created
WIDTH = 800  # Sizing of window
HEIGHT = 600  # Size of window


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(X_COORD, Y_COORD, WIDTH, HEIGHT)
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.setCentralWidget(self.tabs)
        home_widget = QWidget()
        layout = QVBoxLayout()

        self.client = SunbeamClient(settings.sunbeam_api_url)

        # Load and add the team logo
        logo_label = QLabel()
        logo_label.setPixmap(
            QPixmap(str(pathlib.Path(__file__).parent / "Solar_Logo.png")).scaled(800, 600, Qt.KeepAspectRatio)
        )
        logo_label.setAlignment(Qt.AlignCenter)  # Center the image
        layout.addWidget(logo_label)

        # Title Label
        title_label = QLabel("Select Data to Plot")
        title_label.setFont(QFont("Arial", 20))
        layout.addWidget(title_label)

        self.data_select_form = DataSelect()
        layout.addLayout(self.data_select_form)

        # Button to load the plot
        submit_button = QPushButton("Load Data")
        submit_button.clicked.connect(self.create_plot_tab)
        layout.addWidget(submit_button)

        #Settings button
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.edit_settings)
        layout.addWidget(settings_button)

        home_widget.setLayout(layout)
        self.tabs.addTab(home_widget, "Home")

        self.sunbeam_gui = SunbeamTab()
        self.tabs.addTab(self.sunbeam_gui, "Sunbeam")

        self.sunlink_gui = SunlinkTab()
        self.tabs.addTab(self.sunlink_gui, "Sunlink")

        self.telemetry_tab = TelemetryTab()
        self.tabs.addTab(self.telemetry_tab, "Telemetry")

        self.soc_tab = SOCTab()
        self.tabs.addTab(self.soc_tab, "SOC")

        power_button = QPushButton("Load Power Tab")
        power_button.clicked.connect(self.create_power_tab)
        layout.addWidget(power_button)

    def create_plot_tab(self):
        """Creates a PlotTab object. This object contains plots and the toolbar to interact with them.
        This method contains a connection to the request_close method of the PlotTab class to receive
        the signal to close a tab."""

        # Getting the values that we will query.
        origin: str = self.data_select_form.selected_origin
        source: str = self.data_select_form.selected_source
        event: str = self.data_select_form.selected_event
        data_name: str = self.data_select_form.selected_data

        # Creating PlotTab object and adding it to the list of tabs.
        plot_tab = PlotTab(origin, source, event, data_name)
        self.tabs.addTab(plot_tab, f"{data_name}")

        plot_tab.close_requested.connect(self.close_tab)

    def close_tab(self, widget) -> None:
        """
        Closes the current tab.

        :param QWidget widget: an element of the GUI you can interact with. In this case, it is the plot.
        """
        # Checks the index of the tab we want to close; if the tab is not in self.tabs, returns -1
        index: int = self.tabs.indexOf(widget)
        if index != -1:  # Checks that the tab we want to close is in self.tabs. If it isn't (index == -1), do nothing
            self.tabs.removeTab(index)  # If the tab is in self.tabs (index!= -1), we remove it

    def edit_settings(self):
        """Opens a dialog to change the settings of the interface. We can change
        the interval between the data is refreshed, as well as the url from the client
        where we query from."""
        current_interval = settings.plot_timer_interval
        current_client_address = settings.sunbeam_api_url
        current_sunbeam_path = settings.sunbeam_path
        current_sunlink_path = settings.sunlink_path
        current_realtime_event = settings.realtime_event
        current_realtime_pipeline = settings.realtime_pipeline

        dialog = SettingsDialog(
            current_interval,
            current_client_address,
            current_sunbeam_path,
            current_sunlink_path,
            current_realtime_event,
            current_realtime_pipeline,
            self
        )

        if dialog.exec_():  # if user pressed OK
            (
                new_plot_interval,
                new_client_address,
                sunbeam_path,
                sunlink_path,
                realtime_event,
                realtime_pipeline
            ) = dialog.get_settings()

            settings.plot_timer_interval = new_plot_interval
            settings.sunbeam_api_url = new_client_address
            settings.sunbeam_path = sunbeam_path
            settings.sunlink_path = sunlink_path
            settings.realtime_event = realtime_event
            settings.realtime_pipeline = realtime_pipeline

            # Refresh settings
            self.client = SunbeamClient(settings.sunbeam_api_url)
            self.data_select_form.update_filters()

    def on_tab_changed(self, index: int):
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, UpdatableTab):
                widget.set_tab_active(i == index)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QVBoxLayout
from diagnostic_interface.dialog import SettingsDialog
from diagnostic_interface import settings
from diagnostic_interface.tabs import PlotTab, UpdatableTab

import pathlib

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QPushButton, QTabWidget
from data_tools import SunbeamClient
from diagnostic_interface.widgets import DataSelect, SplashOverlay

# Interface aesthetic parameters
WINDOW_TITLE = "Diagnostic Interface"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)

        from diagnostic_interface.tabs import SunbeamTab, SunlinkTab, TelemetryTab, SOCTab, PowerTab, WeatherTab, SpeedTab, ArrayTab

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

        self.power_tab = PowerTab()
        self.tabs.addTab(self.power_tab, "Power")

        self.weather_tab = WeatherTab()
        self.tabs.addTab(self.weather_tab, "Weather")

        self.speed_tab = SpeedTab()
        self.tabs.addTab(self.speed_tab, "Speed")

        self.array_tab = ArrayTab()
        self.tabs.addTab(self.array_tab, "Array")

        pix = QPixmap("Solar_Sun.png").scaled(200, 200, Qt.KeepAspectRatio)
        self._splash = SplashOverlay(self, pix, interval=20)

    def finishSplash(self):
        self._splash.hide()

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

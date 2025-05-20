import pathlib

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QComboBox,
    QFormLayout,
    QVBoxLayout,
    QTabWidget,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from data_tools import SunbeamClient
from diagnostic_interface import TimedWidget, SettingsDialog, PlotTab
from config import settings


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
        form_layout = QFormLayout()

        # Dropdown menus
        self.origin_input = QComboBox()
        self.event_input = QComboBox()
        self.source_input = QComboBox()
        self.data_input = QComboBox()

        self.origin_input.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.event_input.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.source_input.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.data_input.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.origin_input.view().setFixedWidth(200)
        self.event_input.view().setFixedWidth(200)
        self.source_input.view().setFixedWidth(200)
        self.data_input.view().setFixedWidth(200)

        # Load initial data from the API
        self.update_filters()

        # Add to form layout
        form_layout.addRow("Origin:", self.origin_input)
        form_layout.addRow("Event:", self.event_input)
        form_layout.addRow("Source:", self.source_input)
        form_layout.addRow("Data:", self.data_input)

        layout.addLayout(form_layout)

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

        # Callbacks to update dropdowns to only show existing query combinations
        self.origin_input.currentTextChanged.connect(self.update_filters)
        self.event_input.currentTextChanged.connect(self.update_filters)
        self.source_input.currentTextChanged.connect(self.update_filters)

        # Timer to refresh plots
        self.timer = TimedWidget(settings.plot_timer_interval, self.refresh_all_tabs)

    def refresh_all_tabs(self):
        """Refreshes all open plot tabs by requerying data and replotting it."""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, PlotTab):
                widget.refresh_plot()

    def update_filters(self):
        """
        Updates the dropdown options based on the selected values.
        If the API request fails, no data is loaded.
        """
        try:
            # Fetch selected values from the dropdowns

            selected_origin = self.origin_input.currentText()
            selected_source = self.source_input.currentText()
            selected_event = self.event_input.currentText()
            selected_data = self.data_input.currentText()

            # Filter available events, sources, and data types based on selections
            available_origins, available_sources, available_events, available_data = self.filter_data()

            # Update dropdowns
            self.update_dropdown(self.origin_input, available_origins, selected_origin)
            self.update_dropdown(self.event_input, available_events, selected_event)
            self.update_dropdown(self.source_input, available_sources, selected_source)
            self.update_dropdown(self.data_input, available_data, selected_data)

        except Exception as e:
            print(f"Error updating filters: {e}")
            self.clear_dropdowns()

    def filter_data(self) -> tuple[list, list, list, list]:
        """
        Filter the available options for a given field based on selected filters.
        """
        selected_origin = self.origin_input.currentText()
        selected_source = self.source_input.currentText()
        selected_event = self.event_input.currentText()

        available_origins = set(self.client.distinct("origin", {}))

        # Get valid events based on origin
        available_events = set(self.client.distinct("event", {}))
        if selected_origin:
            available_events &= set(self.client.distinct("event", {"origin": selected_origin}))

        # Get valid sources based on origin and event
        available_sources = set(self.client.distinct("source", {}))
        if selected_origin:
            # Filter by origin
            available_sources &= set(self.client.distinct("source", {"origin": selected_origin}))
        if selected_event:
            available_sources &= set(
                self.client.distinct("source", {"event": selected_event})
            )  # Filter by event

        # Get valid data types based on origin, source, and event
        available_data = set(self.client.distinct("name", {}))  # Start with all data
        if selected_origin:
            available_data &= set(
                self.client.distinct("name", {"origin": selected_origin})
            )  # Filter by origin
        if selected_event:
            available_data &= set(
                self.client.distinct("name", {"event": selected_event})
            )  # Filter by event
        if selected_source:
            available_data &= set(
                self.client.distinct("name", {"source": selected_source})
            )  # Filter by source

        # Convert back to lists
        available_origins = list(available_origins)
        available_sources = list(available_sources)
        available_events = list(available_events)
        available_data = list(available_data)

        return available_origins, available_sources, available_events, available_data

    def update_dropdown(self, dropdown: QComboBox, available_data: list, selected_value: str):
        """ Update the dropdown options and select the appropriate value """
        dropdown.blockSignals(True)
        dropdown.clear()
        dropdown.addItems(available_data)

        # Select the previously selected value if available
        if selected_value in available_data:
            dropdown.setCurrentText(selected_value)
        elif available_data:
            dropdown.setCurrentText(available_data[0])  # Select the first available option
        dropdown.blockSignals(False)

    def clear_dropdowns(self):
        """ Clear all dropdowns in case of API failure """
        self.origin_input.clear()
        self.event_input.clear()
        self.source_input.clear()
        self.data_input.clear()

    def create_plot_tab(self):
        """Creates a PlotTab object. This object contains plots and the toolbar to interact with them.
        This method contains a connection to the request_close method of the PlotTab class to receive
        the signal to close a tab."""

        # Getting the values that we will query.
        origin: str = self.origin_input.currentText()
        source: str = self.source_input.currentText()
        event: str = self.event_input.currentText()
        data_name: str = self.data_input.currentText()

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

        dialog = SettingsDialog(current_interval, current_client_address, self)
        if dialog.exec_():  # if user pressed OK
            new_plot_interval, new_client_address = dialog.get_settings()
            self.timer.set_interval(new_plot_interval)

            settings.plot_timer_interval = new_plot_interval

            # Change client
            if new_client_address != current_client_address:
                settings.sunbeam_api_url = new_client_address
                self.client = SunbeamClient(new_client_address)
                self.update_filters()
                self.refresh_all_tabs()

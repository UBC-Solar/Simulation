from plot_tab import PlotTab
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QLabel,
    QComboBox, QFormLayout, QVBoxLayout, QTabWidget)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
from data_tools import SunbeamClient
from timer_widget import TimedWidget

# Interface aesthetic parameters
WINDOW_TITLE = "Diagnostic Interface"
X_COORD = 100 # Sets the x-coord where the interface will be created
Y_COORD = 100 # Sets the y-coord where the interface will be created
WIDTH = 800 # Sizing of window
HEIGHT = 600 # Size of window

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(X_COORD, Y_COORD, WIDTH, HEIGHT)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.create_home_tab()

        # Timer to refresh plots
        self.timer = TimedWidget(120000, self.refresh_all_tabs) # Timer refreshes after 120 seconds

    def refresh_all_tabs(self):
        """Refreshes all open plot tabs by requerying data and replotting it."""
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if isinstance(widget, PlotTab):
                widget.refresh_plot()

    def create_home_tab(self) -> None:
        """
        Creates home tab for the diagnostic interface. The home tab
        contains dropdown menus so that we can choose what data we
        want to query and plot.
        """
        home_widget = QWidget()
        layout = QVBoxLayout()
        client = SunbeamClient()

        # Aesthetic changes
        home_widget.setStyleSheet("background-color: #4bb4de;")

        # Load and add the team logo
        logo_label = QLabel()
        logo_label.setPixmap(QPixmap("Solar_Logo.png").scaled(800, 600, Qt.KeepAspectRatio))
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

        # Load initial data
        self.origins = client.distinct("origin", [])
        self.origin_input.addItems(self.origins)

        self.events = client.distinct("event", [])
        self.event_input.addItems(self.events)

        self.sources = client.distinct("source", [])
        self.source_input.addItems(self.sources)

        self.data_types = client.distinct("name", [])
        self.data_input.addItems(self.data_types)

        # Style of the drowpdown menus
        for combo in [self.origin_input, self.source_input, self.event_input, self.data_input]:
            combo.setStyleSheet("background-color: white")

        # Add to form layout
        form_layout.addRow("Origin:", self.origin_input)
        form_layout.addRow("Event:", self.event_input)
        form_layout.addRow("Source:", self.source_input)
        form_layout.addRow("Data:", self.data_input)

        layout.addLayout(form_layout)

        # Button to load the plot
        submit_button = QPushButton("Load Data")
        submit_button.clicked.connect(self.create_plot_tab)
        submit_button.setStyleSheet("background-color: white")
        layout.addWidget(submit_button)

        home_widget.setLayout(layout)
        self.tabs.addTab(home_widget, "Home")

        # Callbacks to update dropdowns to only show existing query combinations
        self.origin_input.currentTextChanged.connect(self.update_filters)
        self.event_input.currentTextChanged.connect(self.update_filters)
        self.source_input.currentTextChanged.connect(self.update_filters)

    def update_filters(self) -> None:
        """
        Updates all dropdown options based on selected values. This way, you should only
        be able to form query combinations that are available. For example, if you choose
        'realtime' as your origin, in the events dropdown you should only see 'FSGP_2024_Day_1'
        because that is the only event associated with the 'realtime' pipeline.

        :raises Exception: if there is an error while updating the dropdown options.
        """
        try:
            client = SunbeamClient()

            # Initial text
            selected_origin = self.origin_input.currentText()
            selected_source = self.source_input.currentText()
            selected_event = self.event_input.currentText()
            selected_data = self.data_input.currentText()

            # Get valid events based on origin
            available_events = set(client.distinct("event", []))  # Start with all events
            if selected_origin:
                available_events &= set(client.distinct("event", {"origin": selected_origin})) # Filter by origin

            # Get valid sources based on origin and event
            available_sources = set(client.distinct("source", []))  # Start with all
            if selected_origin:
                available_sources &= set(client.distinct("source", {"origin": selected_origin})) # Filter by origin
            if selected_event:
                available_sources &= set(client.distinct("source", {"event": selected_event})) # Filter by event

            # Get valid data types based on origin, source, and event
            available_data = set(client.distinct("name", [])) # Start with all data
            if selected_origin:
                available_data &= set(client.distinct("name", {"origin": selected_origin})) # Filter by origin
            if selected_event:
                available_data &= set(client.distinct("name", {"event": selected_event})) # Filter by event
            if selected_source:
                available_data &= set(client.distinct("name", {"source": selected_source})) # Filter by source

            # Convert back to lists
            available_sources = list(available_sources)
            available_events = list(available_events)
            available_data = list(available_data)

            # Update dropdowns safely
            self.source_input.blockSignals(True) # Shuts down ability to take input
            self.source_input.clear()
            self.source_input.addItems(available_sources)
            # Set the selected source to the first available or keep it if it exists
            if selected_source in available_sources:
                self.source_input.setCurrentText(selected_source)
            elif available_sources:
                self.source_input.setCurrentText(available_sources[0])  # Select first available option
            self.source_input.blockSignals(False) # Can take inputs again

            self.event_input.blockSignals(True) # Can't take inputs
            self.event_input.clear()
            self.event_input.addItems(available_events)
            # Set the selected event to the first available or keep it if it exists
            if selected_event in available_events:
                self.event_input.setCurrentText(selected_event)
            elif available_events:
                self.event_input.setCurrentText(available_events[0])  # Select first available option
            self.event_input.blockSignals(False) # Can take inputs again

            self.data_input.blockSignals(True) # Can't take inputs
            self.data_input.clear()
            self.data_input.addItems(available_data)
            # Set the selected data to the first available or keep it if it exists
            if selected_data in available_data:
                self.data_input.setCurrentText(selected_data)
            elif available_data:
                self.data_input.setCurrentText(available_data[0])  # Select first available option
            self.data_input.blockSignals(False) # Can take inputs again

        except Exception as e:
            print(f"Error updating filters: {e}")

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
        self.tabs.addTab(plot_tab, f"{data_name} - {event} - {origin} - {source}")

        plot_tab.close_requested.connect(self.close_tab)

    def close_tab(self, widget) -> None:
        """
        Closes the current tab.

        :param QWidget widget: an element of the GUI you can interact with. In this case, it is the plot.
        """
        index: int = self.tabs.indexOf(widget) # Checks the index of the tab we want to close; if the tab is not in self.tabs, returns -1
        if index != -1: # Checks that the tab we want to close is in self.tabs. If it isn't (index == -1), do nothing
            self.tabs.removeTab(index) # If the tab is in self.tabs (index!= -1), we remove it
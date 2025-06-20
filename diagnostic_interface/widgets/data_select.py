
from PyQt5.QtWidgets import QComboBox, QFormLayout, QMessageBox
from data_tools import SunbeamClient
from diagnostic_interface import settings
from requests import exceptions as requests_exceptions


class DataSelect(QFormLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

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
        self.addRow("Origin:", self.origin_input)
        self.addRow("Event:", self.event_input)
        self.addRow("Source:", self.source_input)
        self.addRow("Data:", self.data_input)

        # Callbacks to update dropdowns to only show existing query combinations
        self.origin_input.currentTextChanged.connect(self.update_filters)
        self.event_input.currentTextChanged.connect(self.update_filters)
        self.source_input.currentTextChanged.connect(self.update_filters)

    @property
    def selected_origin(self):
        return self.origin_input.currentText()

    @property
    def selected_event(self):
        return self.event_input.currentText()

    @property
    def selected_source(self):
        return self.source_input.currentText()

    @property
    def selected_data(self):
        return self.data_input.currentText()

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

        client = SunbeamClient(settings.sunbeam_api_url)

        try:
            available_origins = set(client.distinct("origin", {}))

            # Get valid events based on origin
            available_events = set(client.distinct("event", {}))
            if selected_origin:
                available_events &= set(client.distinct("event", {"origin": selected_origin}))

            # Get valid sources based on origin and event
            available_sources = set(client.distinct("source", {}))
            if selected_origin:
                # Filter by origin
                available_sources &= set(client.distinct("source", {"origin": selected_origin}))
            if selected_event:
                available_sources &= set(
                    client.distinct("source", {"event": selected_event})
                )  # Filter by event

            # Get valid data types based on origin, source, and event
            available_data = set(client.distinct("name", {}))  # Start with all data
            if selected_origin:
                available_data &= set(
                    client.distinct("name", {"origin": selected_origin})
                )  # Filter by origin
            if selected_event:
                available_data &= set(
                    client.distinct("name", {"event": selected_event})
                )  # Filter by event
            if selected_source:
                available_data &= set(
                    client.distinct("name", {"source": selected_source})
                )  # Filter by source

            # Convert back to lists
            available_origins = list(available_origins)
            available_sources = list(available_sources)
            available_events = list(available_events)
            available_data = list(available_data)

            return available_origins, available_sources, available_events, available_data

        except requests_exceptions.Timeout as e:
            # QMessageBox.critical(None, "Plotting Error", f"Error fetching Sunbeam files:\n{str(e)}")
            return [], [], [], []

    @staticmethod
    def update_dropdown(dropdown: QComboBox, available_data: list, selected_value: str):
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

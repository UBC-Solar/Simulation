import traceback
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox
from diagnostic_interface.tabs.plot_tab import PlotCanvas, CustomNavigationToolbar
from data_tools.query import SunbeamClient


class PowerTab(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.origin_input = parent.data_select_form.origin_input
        self.source_input = parent.data_select_form.source_input
        self.event_input = parent.data_select_form.event_input
        self.tabs = parent.tabs
        self.close_tab = parent.close_tab

        self.setup_ui()
        self.load_power_data()

    def setup_ui(self):
        """Initializes the layout and plot canvases."""
        self.layout = QVBoxLayout()

        # First plot: Power vs Time
        self.power_canvas = PlotCanvas(self)
        power_toolbar = CustomNavigationToolbar(self.power_canvas, self)
        self.layout.addWidget(power_toolbar)
        self.layout.addWidget(self.power_canvas)

        # Second plot: Motor Power vs Track Index per Lap
        self.lap_canvas = PlotCanvas(self)
        lap_toolbar = CustomNavigationToolbar(self.lap_canvas, self)
        self.layout.addWidget(lap_toolbar)
        self.layout.addWidget(self.lap_canvas)

        self.setLayout(self.layout)

    def load_power_data(self):
        """Fetches and plots power-related data from Sunbeam."""
        origin = self.origin_input.currentText()
        source = self.source_input.currentText()
        event = self.event_input.currentText()

        try:
            client = SunbeamClient()

            # Fetch data
            motor_power = client.get_file(origin, "FSGP_2024_Day_1", source, "MotorPower").unwrap().data
            pack_power = client.get_file(origin, "FSGP_2024_Day_1", source, "PackPower").unwrap().data
            gis_indices = client.get_file(origin, "FSGP_2024_Day_1", "localization","TrackIndex").unwrap().data
            lap_numbers = client.get_file(origin, "FSGP_2024_Day_1", "localization",
                                          "LapIndex").unwrap().data

            # Plot: Power vs Time
            self.power_canvas.ax.clear()
            self.power_canvas.ax.plot(motor_power, label="Motor Power")
            self.power_canvas.ax.plot(pack_power, label="Pack Power")
            self.power_canvas.ax.set_title(f"Power vs Time - {event}")
            self.power_canvas.ax.set_xlabel("Time (s)")
            self.power_canvas.ax.set_ylabel("Power (W)")
            self.power_canvas.ax.legend()
            self.power_canvas.draw()

            # Plot: Motor Power vs Track Index per Lap
            self.lap_canvas.ax.clear()
            unique_laps = sorted(set(lap_numbers))
            for lap in unique_laps:
                mask = (lap_numbers == lap)
                self.lap_canvas.ax.plot(gis_indices[mask], motor_power[mask], label=f"Lap {lap}")

            self.lap_canvas.ax.set_title(f"Motor Power per Track Index - {event}")
            self.lap_canvas.ax.set_xlabel("Track Index")
            self.lap_canvas.ax.set_ylabel("Motor Power (W)")
            self.lap_canvas.ax.legend()
            self.lap_canvas.draw()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(
                self.parent,
                "Power Tab Error",
                f"Failed to load power plots.\n\n{str(e)}"
            )
            self.close_tab(self)

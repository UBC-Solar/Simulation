import sys
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTabWidget, QDialog, QMessageBox
)
from PyQt5.QtGui import QPixmap
from diagnostic_interface.config import PersistentConfig
from diagnostic_interface.widgets import SplashOverlay
from simulation.cmd.run_simulation import get_default_settings
from simulation.config import SimulationReturnType, SimulationHyperparametersConfig, InitialConditions
from pathlib import Path
from prescriptive_interface import (SimulationTab, OptimizationTab, SimulationSettingsDict, OptimizationThread,
                                    SimulationThread, MutableInitialConditions, InitialConditionsDialog)
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt

from qt_material import apply_stylesheet

config_dir = Path(__file__).parent.parent / "simulation" / "config"


class SimulationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.tabs: Optional[QTabWidget] = None

        self.simulation_tab: Optional[SimulationTab] = None
        self.optimization_tab: Optional[OptimizationTab] = None
        self.simulation_settings: SimulationSettingsDict = {
            "race_type": "FSGP",
            "verbose": True,
            "granularity": 1,
            "car": "BrightSide"
        }

        self.simulation_thread: Optional[SimulationThread] = None
        self.optimization_thread: Optional[OptimizationThread] = None

        self.initial_conditions = PersistentConfig(
            MutableInitialConditions, config_dir / f"initial_conditions_{self.simulation_settings['race_type']}.toml"
        )

        self.default_initial_conditions, self.default_environment_config, self.default_car_config = get_default_settings(
            self.simulation_settings["race_type"], self.simulation_settings["car"]
        )

        self.default_hyperparameters = SimulationHyperparametersConfig.build_from(
            {
                "simulation_period": 10,
                "return_type": SimulationReturnType.distance_and_time,
                "speed_dt": self.simulation_settings["granularity"],
            }
        )

        self.init_ui()

        pix = QPixmap("Solar_Sun.png").scaled(200, 200, Qt.KeepAspectRatio)
        self._splash = SplashOverlay(self, pix, interval=20)

    def finishSplash(self):
        self._splash.hide()

    def update_lap(self, direction):
        """
        Trigger an update of the lap display on the speed map widget.

        This method delegates the lap navigation command to the FoliumMapWidget,
        which updates the map view based on the given direction.

        :param direction: Either "next" or "prev", indicating the lap to display.
        :type direction: str
        :returns: None
        :rtype: None
        """
        self.optimization_tab.speed_canvas.update_lap(direction)

    def open_settings(self):
        """
        Allows you to change the settings of the optimization.
        """
        self.optimization_tab.speed_canvas.open_settings()

    def prompt_for_initial_conditions(self):
        dialog = InitialConditionsDialog(
            self.initial_conditions, self.default_environment_config.competition_config.date
        )

        if dialog.exec_() == QDialog.Accepted:
            initial_battery_soc, start_time, get_weather, days = dialog.get_values()
            if None not in [initial_battery_soc, start_time, get_weather, days]:
                print(f"Set optimization initial conditions: {initial_battery_soc=}, {start_time=}")
                self.initial_conditions.initial_battery_soc = initial_battery_soc
                self.initial_conditions.start_time = start_time

                if len(days) == 1:
                    if days[0] == 1:
                        QMessageBox.warning(self, "Day Selection Error", "Cannot select Day 1 and 3!")
                        return

                if len(days) == 3:
                    QMessageBox.warning(self, "Day Selection Error", "Must select at least one day!")
                    return

                # TODO: Explain this crap because while it looks to be a mess I promise it
                #   all has a very simple and necessary purpose.
                selected_days = {0, 1, 2} - set(days)
                first_selected_day = min(selected_days)
                minimum_start_time = first_selected_day * 60 * 60 * 24
                start_time = max(minimum_start_time, self.initial_conditions.start_time)

                skipped_days = list(range(0, first_selected_day))
                days = [i for i in days if i not in skipped_days]

                print(f"Start Time: {start_time}")

                # Create an InitialConditions config object form the initial conditions PersistentConfig
                initial_conditions = InitialConditions.build_from(
                    {
                        "current_coord": self.initial_conditions.current_coord,
                        "initial_battery_soc": self.initial_conditions.initial_battery_soc,
                        "start_time": start_time,
                    }
                )
                self.optimize_simulation(initial_conditions, get_weather, days)
            else:
                print("Invalid input.")

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.simulation_tab = SimulationTab(run_callback=self.run_simulation)
        self.optimization_tab = OptimizationTab(
            optimize_callback=self.prompt_for_initial_conditions,
            lap_callback=self.update_lap,
            settings_callback=self.open_settings
        )

        self.tabs.addTab(self.optimization_tab, "Optimization")
        self.tabs.addTab(self.simulation_tab, "Simulation")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setWindowTitle("Prescriptive Interface")

    def run_simulation(self):
        self.simulation_tab.start_button.setEnabled(False)
        self.simulation_tab.sim_output_text.clear()

        self.simulation_thread = SimulationThread(self.simulation_settings, None)
        self.simulation_thread.update_signal.connect(self.simulation_tab.sim_output_text.append)
        self.simulation_thread.plot_data_signal.connect(self.simulation_tab.sim_canvas.plot_simulation_results)
        self.simulation_thread.finished.connect(lambda: self.simulation_tab.start_button.setEnabled(True))

        if self.optimization_thread is not None:
            self.optimization_thread.model_signal.connect(self.optimization_tab.speed_canvas.plot_optimized_speeds)

        self.simulation_thread.start()

    def update_sim_plot(self, results_dict):
        """
        This method passes a dictionary of time series results to the SimulationCanvas,
        which renders them as a grid of plots.

        :param results_dict: Dictionary mapping metric labels to (timestamps, values) tuples.
        :type results_dict: dict
        :returns: None
        :rtype: None
        """
        self.simulation_tab.sim_canvas.plot_simulation_results(results_dict)

    def update_speed_plot(self, model):
        """
        This method visualizes the optimized lap speeds_directory on a folium map by passing
        the model to the FoliumMapWidget.

        :param model: The optimized simulation model containing GIS and speed data.
        :type model: object
        :returns: None
        :rtype: None
        """
        self.optimization_tab.speed_canvas.plot_optimized_speeds(model)

    def optimization_plot(self, model, optimized_speeds, laps_per_index, num_laps):
        """
        Plots optimized speeds on optimization tab. It will then run the simulation with the optimized
        speeds, and display the results in the optimization tab.

        :param model: Optimized simulation model.
        :param optimized_speeds: Array of optimized speeds.
        """
        self.optimization_tab.speed_canvas.plot_optimized_speeds(optimized_speeds, laps_per_index, num_laps)

        # Store optimized speeds
        self.optimized_speeds = optimized_speeds  # Keep as an attribute

        # Run simulation with optimized speeds
        self.simulation_thread = SimulationThread(self.simulation_settings, model=model, speeds_filename=None)
        self.simulation_thread.update_signal.connect(self.simulation_tab.sim_output_text.append)
        self.simulation_thread.plot_data_signal.connect(self.simulation_tab.sim_canvas.plot_simulation_results)

        # Simulation tab will now have the results using the optimized speeds
        self.simulation_thread.optimized_speeds = optimized_speeds

        self.simulation_thread.start()

    def optimize_simulation(self, initial_conditions: InitialConditions, get_weather: bool, days):
        self.optimization_tab.optimize_button.setEnabled(False)
        self.optimization_tab.output_text.clear()

        popsize = self.optimization_tab.speed_canvas.popsize  # Population size for optimization
        maxiter = self.optimization_tab.speed_canvas.maxiter  # Number of iterations for optimization
        self.optimization_thread = OptimizationThread(
            self.simulation_settings,
            popsize,
            maxiter,
            initial_conditions,
            self.default_hyperparameters,
            self.default_environment_config,
            self.default_car_config,
            get_weather,
            days
        )
        self.optimization_tab.progress_bar.setMaximum(maxiter)
        self.optimization_thread.update_signal.connect(self.optimization_tab.output_text.append)
        self.optimization_thread.progress_signal.connect(
            lambda value: self.optimization_tab.progress_bar.setValue(self.optimization_tab.progress_bar.value() + value))
        self.optimization_thread.model_signal.connect(self.optimization_plot)
        self.optimization_thread.finished.connect(lambda: self.optimization_tab.optimize_button.setEnabled(True))

        self.optimization_thread.start()

    def update_output(self, message):
        self.output_text.append(message)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    apply_stylesheet(app, theme='light_blue.xml', invert_secondary=True)

    window = SimulationApp()
    window.showFullScreen()
    window.show()

    window._splash.showMessage("Crimping connectors...")
    QTimer.singleShot(500, lambda: window._splash.showMessage("Recrimping connectors..."))
    QTimer.singleShot(1500, window.finishSplash)

    sys.exit(app.exec_())

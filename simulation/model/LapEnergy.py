import numpy as np
from numpy.typing import NDArray

from simulation.model.Model import Model
from simulation.model.LapGIS import LapGIS
from simulation.model.LapSchedule import LapSchedule
from simulation.race import get_array_directional_wind_speed

# TODO: hardcoded constants
REGEN_MAX_POWER = 4000.0  # W, TODO: not confirmed
BATTERY_MAX_CHARGE_CURRENT = ...  # A, TODO: get this value
BATTERY_VOLTAGE = 115.2  # V, TODO: confirm. Nominal pack voltage (32 cells x 3.6 V); the real one changes with battery %


class LapEnergy:
    """
    Energy used and gained on each lap of a `LapSchedule`. Lap mode's version of tick mode's energy
    step. Weather is read once per lap, at its middle. Motor, drag and regen are worked out per
    stretch of track, then added up per lap.

    After it's built, it holds one value per lap in each of these arrays:
    `motor_energy`, `lvs_energy`, `solar_energy`, `regen_energy` (J), `wind_speed` (m/s),
    `wind_direction` (degrees) and `sunlight` (W/m²).
    """

    def __init__(self, model: Model, gis: LapGIS, schedule: LapSchedule):
        """:param model: the built `Model`, with weather attached (`model._set_weather(...)` until Step 5)."""
        if model.meteorology is None:
            raise ValueError("The model has no weather attached.")
        driving = ~schedule.is_wait # true/false array same length as speed array.

        self.wind_speed, self.wind_direction, self.sunlight = self._weather_per_lap(model, gis, schedule)

        # Every stretch of every driven lap, as one flat list in time order
        # (the physics functions compare each value with the next one)
        speed_ms = schedule.segment_speeds[driving].ravel()
        seconds = schedule.segment_times[driving].ravel()
        motor = self._motor_energy(model, gis, speed_ms, seconds,
                                   self.wind_speed[driving], self.wind_direction[driving])
        regen = self._regen_energy(model, gis, speed_ms, seconds, self.sunlight[driving])

        self.motor_energy = self._add_up_per_lap(motor, driving)
        self.regen_energy = self._add_up_per_lap(regen, driving)
        self.lvs_energy = model.lvs.get_consumed_energy(schedule.duration)
        self.solar_energy = model.solar_array.calculate_produced_energy(self.sunlight, schedule.duration)

    @staticmethod
    def _weather_per_lap(model, gis: LapGIS, schedule: LapSchedule):
        """Wind speed, wind direction and sunlight at the middle of each lap (same local time as tick mode).
        - model holds the start day, schedule holds the time since the start day, gis holds the start line location,
        elevation, and time zone."""
        num_laps = len(schedule.start)
        time_zone = gis.path_time_zones[0]
        local_times = (model.race.date.timestamp() + schedule.start + schedule.duration / 2
                       + time_zone).astype(np.int64)

        weather = model.meteorology
        weather.spatially_localize(np.zeros(num_laps), simplify_weather=True)
        weather.temporally_localize(local_times, model.start_time, 1)
        sunlight = weather.calculate_solar_irradiances(
            np.tile(gis.coords[0], (num_laps, 1)), np.full(num_laps, time_zone),
            local_times, np.full(num_laps, gis.elevations[0]))
        return (np.array(weather.wind_speed, dtype=float), np.array(weather.wind_direction, dtype=float),
                np.array(sunlight, dtype=float))

    @staticmethod
    def _motor_energy(model, gis: LapGIS, speed_ms, seconds, wind_speed, wind_direction) -> NDArray[np.float64]:
        """Motor energy (J) on each stretch, including drag. Wind is one value per driven lap."""
        num_laps = len(wind_speed)
        num_points = len(gis.segment_lengths)
        headings = np.tile(gis.headings, num_laps)
        gradients = np.tile(gis.gradients, num_laps)
        wind_speed = np.repeat(wind_speed, num_points)
        wind_direction = np.repeat(wind_direction, num_points)

        head_wind = get_array_directional_wind_speed(headings, wind_speed, wind_direction)
        attack_angles = wind_direction - (headings + 180)  # same conversion as tick mode
        drag = model.aeroshell.calculate_drag(head_wind, attack_angles, speed_ms)
        down = model.aeroshell.calculate_down(head_wind, attack_angles, speed_ms)
        # tick=1 gives energy per second (the motor's efficiency is only right at 1 s), then × time
        return model.motor.calculate_energy_in(speed_ms * 3.6, gradients, drag, down, 1) * seconds

    @staticmethod
    def _regen_energy(model, gis: LapGIS, speed_ms, seconds, sunlight) -> NDArray[np.float64]:
        """
        Regen energy (J) on each stretch: tick mode's regen, with the limit below in place of its fixed
        10,000 J. Sunlight is one value per driven lap.

        Limit: the battery's spare charging current after the solar array (× voltage, so in W), and never
        more than `REGEN_MAX_POWER`. Times each stretch's seconds to get J.
        """
        num_points = len(gis.segment_lengths)
        elevations = np.tile(gis.elevations, len(sunlight))

        # The physics function compares each stretch with the next, and treats the last one as stopping
        # dead at sea level. Add one more stretch (same speed, back at the start line) so the last real
        # stretch is compared with something sensible, then drop it.
        regen = model.regen.calculate_produced_energy(np.append(speed_ms, speed_ms[-1:]) * 3.6,
                                                      np.append(elevations, gis.elevations[0]), 0.0, np.inf)[:-1]

        array_power = np.repeat(model.solar_array.calculate_produced_energy(sunlight, 1), num_points)
        battery_room = np.maximum(BATTERY_VOLTAGE * BATTERY_MAX_CHARGE_CURRENT - array_power, 0)
        return np.minimum(regen, np.minimum(REGEN_MAX_POWER, battery_room) * seconds)

    @staticmethod
    def _add_up_per_lap(per_stretch, driving) -> NDArray[np.float64]:
        """Add up a flattened list into one value per lap. Waits get 0."""
        per_lap = np.zeros(len(driving))
        per_lap[driving] = per_stretch.reshape(int(driving.sum()), -1).sum(axis=1)
        return per_lap

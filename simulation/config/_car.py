from pydantic import Field
from simulation.config import Config, ConfigDict


class VehicleConfig(Config):
    model_config = ConfigDict(frozen=True)

    vehicle_mass: float            # Vehicle mass in kg


class ArrayConfig(Config):
    model_config = ConfigDict(frozen=True)

    panel_efficiency: float = Field(ge=0.0, le=1.0)  # Efficiency at turning solar irradiance into electrical power
    panel_size: float                                # Effective panel area in in m^2


class LVSConfig(Config):
    model_config = ConfigDict(frozen=True)

    lvs_voltage: float | int    # Voltage of LVS, assumed to be constant
    lvs_current: float | int    # Current consumption of LVS, assumed to be constant


class BatteryConfig(Config):
    model_config = ConfigDict(frozen=True, subclass_field="battery_type")

    battery_type: str


class BatteryModelConfig(BatteryConfig):
    R_0_data: list[float]
    R_P: float
    C_P: float
    Q_total: float
    SOC_data: list[float]
    Uoc_data: list[float]
    max_current_capacity: float
    max_energy_capacity: float


class BasicBatteryConfig(BatteryConfig):
    max_voltage: float              # Maximum voltage of the DayBreak battery pack (V)
    min_voltage: float              # Minimum voltage of the DayBreak battery pack (V)
    max_current_capacity: float     # Nominal capacity of the DayBreak battery pack (Ah)
    max_energy_capacity: float      # Nominal energy capacity of the DayBreak battery pack (Wh)


class MotorConfig(Config):
    model_config = ConfigDict(frozen=True)

    road_friction: float           # Road friction coefficient, dimensionless
    tire_radius: float             # Tire radius, in m
    vehicle_frontal_area: float    # Vehicle frontal area, in m^2
    drag_coefficient: float        # Drag coefficient, dimensionless


class RegenConfig(Config):
    model_config = ConfigDict(frozen=True)


class CarConfig(Config):
    model_config = ConfigDict(frozen=True)

    vehicle_config: VehicleConfig
    array_config: ArrayConfig
    lvs_config: LVSConfig
    battery_config: BatteryConfig
    motor_config: MotorConfig
    regen_config: RegenConfig

    name: str

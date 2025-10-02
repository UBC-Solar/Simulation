from pydantic import Field
from simulation.config.models import Config, ConfigDict


class VehicleConfig(Config):
    """
    Configuration object containing vehicle-wide parameters such as mass, that are not
    specific to a component.

    """

    model_config = ConfigDict(frozen=True)

    vehicle_mass: float  # Vehicle mass in kg
    max_acceleration: float  # Maximum acceleration allowed in m/s^2
    max_deceleration: float  # Maximum deceleration allowed in m/s^2


class ArrayConfig(Config):
    """
    Configuration object describing the solar arrays of a vehicle.
    """

    model_config = ConfigDict(frozen=True)

    panel_efficiency: float = Field(
        ge=0.0, le=1.0
    )  # Efficiency at turning solar irradiance into electrical power
    panel_size: float  # Effective panel area in m^2


class LVSConfig(Config):
    """
    Configuration object describing the low-voltage systems of a vehicle.
    """

    model_config = ConfigDict(frozen=True)

    lvs_voltage: float  # Voltage of LVS, assumed to be constant
    lvs_current: float  # Current consumption of LVS, assumed to be constant


class BatteryConfig(Config):
    """
    Configuration object describing the battery pack of a vehicle.

    Must be built into subclass as specified by `battery_type`.
    """

    model_config = ConfigDict(frozen=True, subclass_field="battery_type")

    battery_type: str


class BatteryModelConfig(BatteryConfig):
    """
    Configuration object describing the battery pack of a vehicle using the first-order Thevenin equivalent
    battery model.
    """

    R_0_data: list[float]
    R_P_data: list[float]
    C_P_data: list[float]
    Q_total: float
    SOC_data: list[float]
    Uoc_data: list[float]


class BasicBatteryConfig(BatteryConfig):
    """
    Configuration object describing the battery pack of a vehicle using a datasheet-based battery model.
    """

    max_voltage: float  # Maximum voltage of the DayBreak battery pack (V)
    min_voltage: float  # Minimum voltage of the DayBreak battery pack (V)
    max_current_capacity: float  # Nominal capacity of the DayBreak battery pack (Ah)
    max_energy_capacity: (
        float  # Nominal energy capacity of the DayBreak battery pack (Wh)
    )


class MotorConfig(Config):
    """
    Configuration object describing the motor of a vehicle.
    """

    model_config = ConfigDict(frozen=True, subclass_field="motor_type")

    motor_type: str

    road_friction: float  # Road friction coefficient, dimensionless
    tire_radius: float  # Tire radius, in m
    vehicle_frontal_area: float  # Vehicle frontal area, in m^2
    drag_coefficient: float  # Drag coefficient, dimensionless


class BasicMotorConfig(MotorConfig):
    pass


class AdvancedMotorConfig(MotorConfig):
    cornering_coefficient: float
    
class AeroshellConfig(Config):
    """
        Configuration object describing the aerodynamics forces (specifically drag and downforce) of a vehicle.
    """
    model_config = ConfigDict(frozen=True)
    drag_lookup: dict[float:float] #lookup table that corresponds angles to drag force, computed by a CFD
    down_lookup: dict[float:float] #lookup table that corresponds angles to down force, computed by a CFD

class RegenConfig(Config):
    """
    Configuration object describing the regenerative braking systems of a vehicle.
    """

    model_config = ConfigDict(frozen=True)


class CarConfig(Config):
    """
    Configuration object completely specifying the aspects of a solar-powered vehicle.
    """

    model_config = ConfigDict(frozen=True)

    vehicle_config: VehicleConfig
    array_config: ArrayConfig
    lvs_config: LVSConfig
    battery_config: BatteryConfig
    motor_config: MotorConfig
    regen_config: RegenConfig
    aeroshell_config: AeroshellConfig

    name: str

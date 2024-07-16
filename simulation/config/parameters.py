from typing import List
#######################################################################################
#                                                                                     #
#           In order to add new parameters, add the parameter in the PARAMETERS       #
#           section, and then add it to the appropriate model in MODEL LOOKUP         #
#                                                                                     #
#######################################################################################


###################################  PARAMETERS  ######################################


# Note: before performing curve fitting, these parameters should set to whatever
# value such that they have NO EFFECT on the system.
# Example: For polynomial scaling coefficients, the constant factor should be 1.0,
# and all others should be 0.0.

MOTOR_ACCELERATION_LINEAR_FACTOR = 0.0
MOTOR_ACCELERATION_CONSTANT_FACTOR = 1.0
MOTOR_POWER_LINEAR_FACTOR = 0.0
MOTOR_POWER_CONSTANT_FACTOR = 1.0

ARRAY_POWER_LINEAR_FACTOR = 0.0
ARRAY_POWER_CONSTANT_FACTOR = 1.0

LVS_CONSTANT_FACTOR = 1.0

REGEN_SPEED_CUTOFF = 0.0      # Units: m/s
REGEN_POWER_CUTOFF = 100000   # Units: W
REGEN_LINEAR_FACTOR = 0.0
REGEN_CONSTANT_FACTOR = 1.

CORNERING_LOSSES_FACTOR = 1


###################################    LOOKUP    ######################################


parameters = {
    "BasicMotor": [MOTOR_ACCELERATION_LINEAR_FACTOR, MOTOR_ACCELERATION_CONSTANT_FACTOR, MOTOR_POWER_LINEAR_FACTOR, MOTOR_POWER_CONSTANT_FACTOR, CORNERING_LOSSES_FACTOR],
    "BasicLVS": [LVS_CONSTANT_FACTOR],
    "BasicArray": [ARRAY_POWER_LINEAR_FACTOR, ARRAY_POWER_CONSTANT_FACTOR],
    "BasicBattery": [],
    "BasicRegen": [REGEN_SPEED_CUTOFF, REGEN_POWER_CUTOFF, REGEN_LINEAR_FACTOR, REGEN_CONSTANT_FACTOR]
}


def get_parameters(model_name: str) -> List[float]:
    """
    For a given ``model_name``, return the associated set of parameters as a list.
    Raises an ``AssertionError`` if the model couldn't be found in the map of parameters in `config/parameters.py`.
    """
    assert model_name in parameters.keys(), f"{model_name} not in parameters!"

    return parameters[model_name]

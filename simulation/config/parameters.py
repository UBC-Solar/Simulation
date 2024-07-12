from typing import List
#######################################################################################
#                                                                                     #
#           In order to add new parameters, add the parameter in the PARAMETERS       #
#           section, and then add it to the appropriate model in MODEL LOOKUP         #
#                                                                                     #
#######################################################################################


###################################  PARAMETERS  ######################################


MOTOR_ACCELERATION_LINEAR_FACTOR = 0.0
MOTOR_ACCELERATION_CONSTANT_FACTOR = 1.0
MOTOR_POWER_LINEAR_FACTOR = 0.0
MOTOR_POWER_CONSTANT_FACTOR = 1.0


###################################    LOOKUP    ######################################


parameters = {
    "BasicMotor": [MOTOR_ACCELERATION_LINEAR_FACTOR, MOTOR_ACCELERATION_CONSTANT_FACTOR, MOTOR_POWER_LINEAR_FACTOR, MOTOR_POWER_CONSTANT_FACTOR],
    "BasicLVS": [],
    "BasicArray": [],
    "BasicBattery": [],
    "BasicRegen": []
}


def get_parameters(model_name: str) -> List[float]:
    """
    For a given ``model_name``, return the associated set of parameters as a list.
    Raises an ``AssertionError`` if the model couldn't be found in the map of parameters in `config/parameters.py`.
    """
    assert model_name in parameters.keys(), f"{model_name} not in parameters!"

    return parameters[model_name]

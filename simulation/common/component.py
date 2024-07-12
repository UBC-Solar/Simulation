from abc import ABC
from simulation.config.parameters import get_parameters


class Component(ABC):
    """
    The base component model
    """

    def __init__(self):
        model_class_name = str(self.__class__).split('.')[-1].removesuffix("'>")
        self.parameters = get_parameters(model_class_name)


from abc import ABC, abstractmethod
from ..common import Producer

class BaseRegen(Producer):
    def __init__(self):
        super().__init__(self)
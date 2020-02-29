from abc import ABC, abstractmethod
from ..common import Storage

class BaseBattery(Storage):
    def __init__(self):
        super().__init__(self)
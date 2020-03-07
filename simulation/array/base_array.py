from abc import ABC, abstractmethod
from ..common import Producer

class BaseArray(Producer):
    def __init__(self):
        super().__init__(self)
        # do array initialization
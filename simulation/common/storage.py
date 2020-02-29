from abc import ABC, abstractmethod

class Storage(ABC): 
    """
    The base storage model

    :param 
    """
    def __init__(self, stored_energy=0):
        self.stored_energy = stored_energy
        
    @abstractmethod
    def update(self, tick):

        pass

    @abstractmethod 
    def charge(self, energy):

        pass

    @abstractmethod 
    def discharge(self, energy):

        pass
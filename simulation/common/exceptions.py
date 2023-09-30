"""
Contains all the custom exceptions used in the simulation package
"""


class BatteryEmptyError(Exception):
    pass


class LibrariesNotFound(Exception):
    pass

class PrematureDataRecoveryError(Exception):
    pass

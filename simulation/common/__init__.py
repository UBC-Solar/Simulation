from simulation.common.consumer import Consumer
from simulation.common.exceptions import BatteryEmptyError, PrematureDataRecoveryError
from simulation.common.helpers import timeit
from simulation.common.producer import Producer
from simulation.common.storage import Storage
from simulation.common.car import Car

DayBreak = Car('DayBreak')
BrightSide = Car('BrightSide')

from simulation.common.consumer import Consumer
from simulation.common.exceptions import BatteryEmptyError
from simulation.common.exceptions import PrematureDataRecoveryError
from simulation.common.helpers import timeit
from simulation.common.producer import Producer
from simulation.common.storage import Storage
from simulation.common.car import Car
from simulation.common.race import Race
from simulation.common.equations import DayBreakEquations

DayBreak = Car('DayBreak')
BrightSide = Car('BrightSide')
ASC = Race('ASC')
FSGP = Race('FSGP')

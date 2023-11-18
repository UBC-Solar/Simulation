from simulation.common.consumer import Consumer
from simulation.common.exceptions import BatteryEmptyError, PrematureDataRecoveryError
from simulation.common.producer import Producer
from simulation.common.storage import Storage
from simulation.common.car import Car
from simulation.common.race import Race
from simulation.common.equations import DayBreakEquations

DayBreak = Car('DayBreak')
BrightSide = Car('BrightSide')
ASC = Race('ASC')
FSGP = Race('FSGP')

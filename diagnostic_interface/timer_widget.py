from PyQt5.QtCore import QTimer
from typing import Callable


class TimedWidget:
    """A TimedWidget is a timer that instructs the application
    to update once the time it is set to elapses."""
    def __init__(self, interval: int, callback: Callable):
        """ Instantiate a TimedWidget.

        :param int interval: the time interval between updates.
        :param Callable callback: the function to be called on timeout.
        """
        self.timer = QTimer()
        self.interval = interval
        self.timer.timeout.connect(callback)
        self.timer.start(interval)

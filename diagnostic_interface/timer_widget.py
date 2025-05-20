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
        self.interval = interval * 1000
        self.timer.timeout.connect(callback)

        # Delay starting the timer until the event loop has fully initialized
        QTimer.singleShot(0, self.start_timer)  # Starts the timer after the event loop is ready

    def start_timer(self):
        """Start the timer."""
        self.timer.start(self.interval)

    def set_interval(self, interval: int):
        """Update the timer interval and restart the timer."""
        self.interval = interval * 1000
        self.timer.stop()  # Stop the current timer
        self.timer.start(interval)  # Restart the timer with the new interval

    def stop(self):
        """Stop the timer."""
        self.timer.stop()

    def start(self):
        """Start the timer with the current interval."""
        self.timer.start(self.interval)

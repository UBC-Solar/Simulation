from PyQt5.QtCore import QTimer


class TimedWidget:
    def __init__(self, interval, callback):
        self.timer = QTimer()
        self.timer.timeout.connect(callback)
        self.timer.start(interval)

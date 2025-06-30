from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QPixmap, QPainter, QTransform
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout


class SplashOverlay(QWidget):
    def __init__(self, parent, pixmap: QPixmap, interval=30):
        super().__init__(parent)
        # make sure it’s on top of everything
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.raise_()

        self._pixmap = pixmap
        self._angle  = 0

        # message label
        self._message_label = QLabel("", self)
        self._message_label.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        self._message_label.setStyleSheet("color: black; font-size: 14pt;")
        self._message_label.setContentsMargins(0,0,0,20)

        # layout: stretch + label at the bottom
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addStretch()
        layout.addWidget(self._message_label)
        self.setLayout(layout)

        # animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(interval)

        # resize with parent
        parent.installEventFilter(self)
        self.resize(parent.size())

    def eventFilter(self, obj, ev):
        if obj is self.parent() and ev.type() == QEvent.Resize:
            self.resize(ev.size())
        return super().eventFilter(obj, ev)

    def _animate(self):
        self._angle = (self._angle + 5) % 360
        self.update()   # trigger paintEvent

    def paintEvent(self, ev):
        painter = QPainter(self)
        # white background
        painter.fillRect(self.rect(), Qt.white)
        # rotated pixmap
        rotated = self._pixmap.transformed(
            QTransform().rotate(self._angle),
            Qt.SmoothTransformation
        )
        x = (self.width()  - rotated.width())  // 2
        y = (self.height() - rotated.height()) // 2
        painter.drawPixmap(x, y, rotated)
        painter.end()

    def showMessage(self, text: str):
        """Just like QSplashScreen.showMessage."""
        self._message_label.setText(text)
        # ensure it repaints immediately
        self._message_label.repaint()


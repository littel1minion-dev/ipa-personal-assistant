from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QLabel, QMainWindow, QWidget


class HudWidget(QWidget):
    def __init__(self, assistant_name: str = "I.P.A."):
        super().__init__()
        self.setWindowTitle("Ian's Personal Assistant")
        self.resize(900, 600)
        self.assistant_name = assistant_name
        self.status = "idle"
        self._angle = 0.0

        self.title = QLabel(assistant_name, self)
        self.title.setStyleSheet("font-size: 24px; color: #f4d29d; letter-spacing: 3px;")
        self.title.move(20, 20)

    def set_status(self, status: str) -> None:
        self.status = status
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(11, 18, 28)
        painter.fillRect(self.rect(), bg)

        cx = self.width() / 2
        cy = self.height() / 2 - 30
        radius = min(self.width(), self.height()) * 0.22

        glow = QColor(244, 174, 79, 90)
        painter.setPen(QPen(glow, 1))
        painter.setBrush(glow)
        painter.drawEllipse(int(cx - radius * 1.7), int(cy - radius * 1.7), int(radius * 3.4), int(radius * 3.4))

        core = QColor(255, 183, 76)
        painter.setPen(QPen(core, 2))
        painter.setBrush(core)
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        ring_color = QColor(255, 225, 170)
        painter.setPen(QPen(ring_color, 1))
        painter.drawEllipse(int(cx - radius * 1.5), int(cy - radius * 1.5), int(radius * 3), int(radius * 3))

        painter.setPen(QPen(QColor(237, 174, 96), 2))
        painter.drawArc(int(cx - radius * 1.15), int(cy - radius * 1.15), int(radius * 2.3), int(radius * 2.3), 0, 360 * 16)

        self._angle += 0.06
        painter.translate(cx, cy)
        painter.rotate(self._angle * 30)
        painter.setPen(QPen(QColor(255, 214, 147), 2))
        for i in range(12):
            x = (i % 3) * 18
            y = (i // 3) * 18
            painter.drawLine(0, -radius * 1.15, 0, -radius * 1.7)
            painter.rotate(30)

        painter.end()

        status = self.status.upper()
        painter = QPainter(self)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, status)

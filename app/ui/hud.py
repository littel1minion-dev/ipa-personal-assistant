from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, QTimer, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget


class HudWidget(QWidget):
    """Original, software-drawn amber holographic core."""

    def __init__(self, assistant_name: str = "I.P.A."):
        super().__init__()
        self.assistant_name = assistant_name
        self.status = "idle"
        self.level = 0.0
        self.phase = 0.0
        self.setMinimumHeight(300)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(16)

    def set_status(self, status: str) -> None:
        self.status = status.lower()
        self.update()

    def _step(self) -> None:
        self.phase = (self.phase + 0.012) % (2 * math.pi)
        target = 0.28 if self.status == "listening" else 0.0
        self.level += (target - self.level) * 0.08
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#071018"))
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 + 3
        radius = min(w * 0.26, h * 0.37)
        breath = 1.0 + 0.018 * math.sin(self.phase * 1.5) + self.level * 0.04
        r = radius * breath

        # Soft atmospheric glow.
        halo = QRadialGradient(QPointF(cx, cy), r * 2.25)
        halo.setColorAt(0.0, QColor(238, 142, 43, 62))
        halo.setColorAt(0.55, QColor(155, 79, 24, 25))
        halo.setColorAt(1.0, QColor(5, 10, 16, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(halo))
        p.drawEllipse(QPointF(cx, cy), r * 2.25, r * 2.25)

        # Rotating elliptical orbit lines, drawn as two tilted projector rings.
        p.save()
        p.translate(cx, cy)
        p.rotate(math.sin(self.phase * 0.42) * 9)
        for idx, (scale, tilt, direction) in enumerate(((1.48, 62, 1), (1.22, -58, -1), (0.92, 0, 1))):
            p.save()
            p.rotate(tilt)
            p.rotate(math.degrees(self.phase) * direction * (0.55 + idx * 0.12))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(246, 157 + idx * 12, 57, 110 - idx * 17), 1.2 if idx == 0 else 0.9))
            p.drawEllipse(QRectF(-r * scale, -r * scale * 0.36, r * scale * 2, r * scale * 0.72))
            # Moving light on the ring.
            a = self.phase * direction * (1.5 + idx * 0.3)
            sx, sy = math.cos(a) * r * scale, math.sin(a) * r * scale * 0.36
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 219, 148, 225))
            p.drawEllipse(QPointF(sx, sy), 2.0 + idx * 0.4, 2.0 + idx * 0.4)
            p.restore()
        p.restore()

        # Glass sphere with a warm central light and fine latitude arcs.
        sphere = QRadialGradient(QPointF(cx - r * 0.28, cy - r * 0.34), r * 1.5)
        sphere.setColorAt(0.0, QColor(255, 224, 160, 92))
        sphere.setColorAt(0.28, QColor(245, 153, 55, 55))
        sphere.setColorAt(0.76, QColor(189, 92, 30, 20))
        sphere.setColorAt(1.0, QColor(255, 152, 46, 8))
        p.setPen(QPen(QColor(255, 184, 99, 185), 1.1))
        p.setBrush(QBrush(sphere))
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 194, 113, 48), 0.8))
        p.drawEllipse(QRectF(cx - r * 0.83, cy - r * 0.31, r * 1.66, r * 0.62))
        p.drawEllipse(QRectF(cx - r * 0.63, cy - r * 0.58, r * 1.26, r * 1.16))

        heart_r = r * (0.16 + self.level * 0.16 + 0.018 * math.sin(self.phase * 2))
        heart = QRadialGradient(QPointF(cx, cy), heart_r * 2.8)
        heart.setColorAt(0.0, QColor(255, 245, 211, 240))
        heart.setColorAt(0.22, QColor(255, 181, 81, 185))
        heart.setColorAt(1.0, QColor(240, 120, 32, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(heart))
        p.drawEllipse(QPointF(cx, cy), heart_r * 2.8, heart_r * 2.8)
        p.setPen(QPen(QColor("#ffe2b5")))
        p.drawText(QRectF(0, cy + r * 1.22, w, 24), Qt.AlignmentFlag.AlignCenter, self.status.upper())
        p.end()

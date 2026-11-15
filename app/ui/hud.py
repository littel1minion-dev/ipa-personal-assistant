from __future__ import annotations

import math
import random

from PyQt6.QtCore import QPointF, QRectF, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget


class HudWidget(QWidget):
    """Animated, software-rendered amber particle-core HUD.

    The scene is procedurally drawn and original; it does not use or reproduce
    the artwork from the reference image. Particle positions are generated once
    and projected with a slowly rotating sphere transform each frame.
    """

    PARTICLE_COUNT = 1250

    def __init__(self, assistant_name: str = "I.P.A."):
        super().__init__()
        self.assistant_name = assistant_name
        self.status = "idle"
        self.phase = 0.0
        self.level = 0.0
        self._rng = random.Random(57031)
        self._particles = self._make_particles()
        self.setMinimumHeight(330)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(16)

    def _make_particles(self) -> list[tuple[float, float, float, float, float]]:
        """Distribute particles over a shell, with some denser orbital bands."""
        result = []
        golden_angle = math.pi * (3.0 - math.sqrt(5.0))
        for i in range(self.PARTICLE_COUNT):
            y = 1.0 - 2.0 * (i + 0.5) / self.PARTICLE_COUNT
            ring_radius = math.sqrt(max(0.0, 1.0 - y * y))
            angle = golden_angle * i + self._rng.uniform(-0.035, 0.035)
            # Slightly rough shell gives the projected energy field a less
            # mathematically perfect, more holographic silhouette.
            shell = self._rng.uniform(0.78, 1.035)
            x = math.cos(angle) * ring_radius * shell
            z = math.sin(angle) * ring_radius * shell
            y *= shell
            size = self._rng.choices((0.55, 0.8, 1.0, 1.5, 2.0), (12, 35, 35, 15, 3))[0]
            energy = self._rng.random()
            result.append((x, y, z, size, energy))

        # A few glowing currents form irregular, orbital-looking filaments.
        for strand in range(7):
            tilt = self._rng.uniform(-0.7, 0.7)
            offset = self._rng.uniform(0, math.tau)
            for j in range(85):
                t = j / 84 * math.tau
                radius = self._rng.uniform(0.58, 1.0)
                x = math.cos(t + offset + strand * 0.37) * radius
                z = math.sin(t + offset + strand * 0.37) * radius
                y = math.sin(t * (1.3 + strand * 0.08) + tilt) * 0.28
                result.append((x, y, z, self._rng.uniform(0.65, 1.7), self._rng.uniform(0.5, 1.0)))
        return result

    def set_status(self, status: str) -> None:
        self.status = status.lower()
        self.update()

    def set_audio_level(self, level: float) -> None:
        """Set normalized audio intensity (0..1) for future mic/output wiring."""
        self.level = max(0.0, min(1.0, float(level)))
        self.update()

    def _step(self) -> None:
        self.phase = (self.phase + 0.018) % math.tau
        if self.status not in {"listening", "speaking"}:
            self.level *= 0.92
        else:
            # Subtle procedural shimmer until microphone/output amplitude is wired.
            self.level = max(self.level * 0.96, 0.035 + 0.025 * (0.5 + 0.5 * math.sin(self.phase * 3.1)))
        self.update()

    @staticmethod
    def _color(alpha: float, hot: float = 0.0) -> QColor:
        a = max(0, min(255, int(alpha)))
        if hot > 0.76:
            return QColor(255, 232, 173, a)
        if hot > 0.48:
            return QColor(255, 176, 75, a)
        return QColor(235, 105, 28, a)

    def _draw_frame(self, p: QPainter, w: float, h: float) -> None:
        """Fine amber corner guides and understated telemetry rails."""
        p.save()
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(132, 71, 31, 115), 1))
        margin = 17.0
        corner = 24.0
        # Four separated corner brackets, deliberately lighter than the core.
        for x, y, sx, sy in ((margin, margin, 1, 1), (w-margin, margin, -1, 1),
                             (margin, h-margin, 1, -1), (w-margin, h-margin, -1, -1)):
            p.drawLine(QPointF(x, y), QPointF(x + sx * corner, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + sy * corner))
        p.setPen(QPen(QColor(98, 61, 35, 90), 1))
        p.drawLine(QPointF(margin + 30, h - 24), QPointF(w * 0.37, h - 24))
        p.drawLine(QPointF(w * 0.64, h - 24), QPointF(w - margin - 30, h - 24))
        p.setPen(QPen(QColor(224, 135, 57, 150), 2))
        p.drawLine(QPointF(margin + 30, h - 24), QPointF(margin + 30 + (w * 0.18), h - 24))
        p.restore()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w, h = float(self.width()), float(self.height())

        # Near-black field with a faint warm center, avoiding a flat black fill.
        p.fillRect(self.rect(), QColor("#060908"))
        bg = QRadialGradient(QPointF(w * 0.5, h * 0.48), max(w, h) * 0.62)
        bg.setColorAt(0.0, QColor(35, 19, 9, 100))
        bg.setColorAt(0.55, QColor(13, 12, 9, 48))
        bg.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), bg)
        self._draw_frame(p, w, h)

        # Top instrument rail and tiny state marker.
        rail_x, rail_y = 32.0, 31.0
        rail_w = max(100.0, w - 64.0)
        p.setPen(QPen(QColor(91, 60, 35, 190), 1))
        p.setBrush(QColor(11, 12, 10, 210))
        p.drawRoundedRect(QRectF(rail_x, rail_y, rail_w, 15), 2, 2)
        fill = QLinearGradient(rail_x, 0, rail_x + rail_w, 0)
        fill.setColorAt(0.0, QColor(235, 119, 38, 220))
        fill.setColorAt(0.62, QColor(173, 79, 24, 150))
        fill.setColorAt(1.0, QColor(69, 37, 18, 30))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fill)
        p.drawRect(QRectF(rail_x + 2, rail_y + 3, rail_w * 0.68, 3))
        p.setPen(QPen(QColor(255, 187, 104, 210), 1))
        p.drawRect(QRectF(rail_x + 2, rail_y + 10, rail_w * 0.22, 2))
        p.setBrush(QColor(20, 15, 10, 230))
        p.setPen(QPen(QColor(125, 86, 49, 170), 1))
        p.drawRect(QRectF(rail_x + rail_w - 22, rail_y + 3, 15, 8))

        # Particle sphere perspective projection.
        cx, cy = w * 0.5, h * 0.51
        radius = min(w * 0.315, h * 0.405)
        pulse = 1.0 + 0.016 * math.sin(self.phase * 1.2) + self.level * 0.045
        radius *= pulse
        rotation = self.phase * 0.24
        cos_r, sin_r = math.cos(rotation), math.sin(rotation)
        points: list[tuple[float, float, float, float, float]] = []
        for x, y, z, size, energy in self._particles:
            xr = x * cos_r - z * sin_r
            zr = x * sin_r + z * cos_r
            # Small independent wobble makes the energy field feel alive.
            yr = y + 0.025 * math.sin(self.phase * 1.7 + x * 9.0)
            depth = 1.0 / (1.18 - zr * 0.20)
            px = cx + xr * radius * depth
            py = cy + yr * radius * depth
            points.append((zr, px, py, size * depth, energy))
        points.sort(key=lambda point: point[0])

        # Atmospheric halo.
        halo = QRadialGradient(QPointF(cx, cy), radius * 1.5)
        halo.setColorAt(0.0, QColor(239, 117, 34, 30))
        halo.setColorAt(0.58, QColor(210, 78, 21, 17))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, cy), radius * 1.5, radius * 1.5)

        # A few sweeping paths imply flowing energy without requiring image assets.
        for band in range(10):
            path = QPainterPath()
            start = -math.pi * 0.82 + band * 0.12 + self.phase * (0.1 if band % 2 else -0.08)
            for step in range(90):
                t = start + step / 89 * math.pi * 1.8
                wobble = 0.018 * math.sin(t * 7 + band + self.phase * 1.8)
                rr = radius * (0.72 + band * 0.023 + wobble)
                xx = cx + math.cos(t) * rr
                yy = cy + math.sin(t) * rr * (0.8 + 0.04 * math.sin(band))
                if step == 0:
                    path.moveTo(xx, yy)
                else:
                    path.lineTo(xx, yy)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(242, 116 + band * 5, 35, 17 + (band % 3) * 7), 0.7))
            p.drawPath(path)

        # Depth-aware points: back side is dim, front side has crisp hot sparks.
        for depth, x, y, size, energy in points:
            front = max(0.0, min(1.0, (depth + 1.0) * 0.5))
            alpha = (22 + energy * 135) * (0.25 + 0.75 * front)
            dot = max(0.7, min(2.5, size * (0.65 + energy * 0.8)))
            if energy > 0.92 and front > 0.65:
                p.setPen(QPen(QColor(255, 188, 95, int(alpha * 0.16)), dot * 3.2))
                p.drawPoint(QPointF(x, y))
            p.setPen(QPen(self._color(alpha, energy), dot))
            p.drawPoint(QPointF(x, y))

        # Core glow and nested gyroscopic rings.
        core_r = radius * (0.17 + self.level * 0.035)
        core = QRadialGradient(QPointF(cx, cy), core_r * 3.8)
        core.setColorAt(0.0, QColor(255, 248, 218, 245))
        core.setColorAt(0.12, QColor(255, 196, 103, 210))
        core.setColorAt(0.42, QColor(255, 125, 36, 105))
        core.setColorAt(1.0, QColor(222, 72, 20, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(core)
        p.drawEllipse(QPointF(cx, cy), core_r * 3.8, core_r * 3.8)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 194, 110, 125), 1))
        p.drawEllipse(QRectF(cx - core_r * 1.25, cy - core_r * 0.53, core_r * 2.5, core_r * 1.06))
        p.save()
        p.translate(cx, cy)
        p.rotate(-math.degrees(self.phase * 0.7))
        p.setPen(QPen(QColor(255, 145, 57, 85), 1))
        p.drawEllipse(QRectF(-core_r * 1.65, -core_r * 0.46, core_r * 3.3, core_r * 0.92))
        p.restore()

        # Four screen-space brackets frame the orb, like a scanner reticle.
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(186, 98, 41, 90), 1))
        br = radius * 1.34
        length = 22
        for x, y, sx, sy in ((cx-br, cy-br, 1, 1), (cx+br, cy-br, -1, 1),
                             (cx-br, cy+br, 1, -1), (cx+br, cy+br, -1, -1)):
            p.drawLine(QPointF(x, y), QPointF(x + sx * length, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + sy * length))

        # Original app identity and state label.
        p.setPen(QColor(232, 160, 88, 225))
        font = QFont("Menlo", 9)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        p.setFont(font)
        p.drawText(QRectF(30, 55, w - 60, 20), Qt.AlignmentFlag.AlignLeft, self.assistant_name.upper())
        p.setPen(QColor(233, 172, 103, 205))
        p.drawText(QRectF(0, cy + radius * 1.43, w, 24), Qt.AlignmentFlag.AlignCenter, self.status.upper())
        p.setPen(QColor(129, 83, 47, 135))
        small_font = QFont("Menlo", 7)
        p.setFont(small_font)
        p.drawText(QRectF(20, h - 39, w - 40, 13), Qt.AlignmentFlag.AlignCenter,
                   "LOCAL CORE  ·  " + ("AUDIO READY" if self.status in {"listening", "speaking"} else "STANDBY"))
        p.end()

"""
neon_orb.py
Круглый неоновый индикатор в центре главного окна: пульсирует, когда
ассистент слушает, светится ровно, когда он говорит, и тускнеет в состоянии
покоя. Реализован через QPainter + QPropertyAnimation, без внешних ассетов.
"""

from __future__ import annotations

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtProperty, QEasingCurve, QPropertyAnimation
    from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen
    from PyQt6.QtWidgets import QWidget
except ImportError:  # pragma: no cover
    from PySide6.QtCore import Qt, QTimer, Property as pyqtProperty, QEasingCurve, QPropertyAnimation
    from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen
    from PySide6.QtWidgets import QWidget

from ui.theme import ACCENT, ACCENT_2, ACCENT_PINK, TEXT_SECONDARY


class NeonOrb(QWidget):
    STATE_COLORS = {
        "idle": TEXT_SECONDARY,
        "listening": ACCENT_2,
        "processing": ACCENT,
        "speaking": ACCENT_PINK,
        "error": "#ff3860",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self._scale = 0.85
        self._state = "idle"
        self._pulse_dir = 1

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def set_state(self, state: str):
        self._state = state if state in self.STATE_COLORS else "idle"
        self.update()

    def _tick(self):
        # Плавная пульсация только в состояниях listening/processing/speaking
        if self._state == "idle":
            target = 0.85
            self._scale += (target - self._scale) * 0.08
        else:
            speed = 0.015 if self._state == "listening" else 0.03
            self._scale += speed * self._pulse_dir
            if self._scale > 1.05:
                self._pulse_dir = -1
            elif self._scale < 0.85:
                self._pulse_dir = 1
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base_radius = min(w, h) / 2 * 0.55
        radius = base_radius * self._scale

        color = QColor(self.STATE_COLORS[self._state])

        # Внешнее свечение
        glow = QRadialGradient(cx, cy, radius * 2.1)
        glow_color = QColor(color)
        glow_color.setAlpha(140)
        glow.setColorAt(0.0, glow_color)
        transparent = QColor(color)
        transparent.setAlpha(0)
        glow.setColorAt(1.0, transparent)
        painter.setBrush(glow)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - radius * 2.1), int(cy - radius * 2.1), int(radius * 4.2), int(radius * 4.2))

        # Ядро
        core_gradient = QRadialGradient(cx, cy, radius)
        core_gradient.setColorAt(0.0, QColor("#ffffff"))
        core_gradient.setColorAt(0.35, color)
        core_dark = QColor(color).darker(220)
        core_gradient.setColorAt(1.0, core_dark)
        painter.setBrush(core_gradient)
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

        painter.end()

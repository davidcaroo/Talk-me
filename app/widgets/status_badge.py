"""Status badge widget with glowing luminescent indicators inspired by visionOS."""

import math
from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QRadialGradient
from PySide6.QtWidgets import QWidget

from models.app_state import AppState


class StatusBadge(QWidget):
    """Luminescent circular status indicator with aura glow and pulse animations."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._state: AppState = AppState.IDLE
        self._phase: float = 0.0

        self.setFixedSize(22, 22)
        self.setAttribute(Qt.WA_Hover, False)

        # Pulse animation timer
        self._timer = QTimer(self)
        self._timer.setInterval(25)  # 40 FPS
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    @property
    def state(self) -> AppState:
        return self._state

    def set_state(self, state: AppState) -> None:
        """Sets current state and triggers repaint."""
        if self._state == state:
            return
        self._state = state
        self.update()

    def _on_tick(self) -> None:
        """Ticks pulsing aura phase."""
        self._phase += 0.08
        if self._phase > 2 * math.pi * 100:
            self._phase = 0.0
        if self._state in (AppState.LISTENING, AppState.TRANSCRIBING, AppState.PAUSED):
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Renders glowing status indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        pulse = 0.5 + 0.5 * math.sin(self._phase * 2.0)

        # Color palette per state
        if self._state == AppState.LISTENING:
            primary = QColor(16, 185, 129)      # Emerald / Green
            glow = QColor(16, 185, 129, int(50 + 40 * pulse))
        elif self._state == AppState.PAUSED:
            primary = QColor(245, 158, 11)     # Amber
            glow = QColor(245, 158, 11, int(40 + 30 * pulse))
        elif self._state == AppState.TRANSCRIBING:
            primary = QColor(56, 189, 248)     # Sky Blue
            glow = QColor(56, 189, 248, int(60 + 50 * pulse))
        elif self._state == AppState.DONE:
            primary = QColor(16, 185, 129)     # Emerald
            glow = QColor(16, 185, 129, 60)
        elif self._state == AppState.ERROR:
            primary = QColor(239, 68, 68)      # Crimson Red
            glow = QColor(239, 68, 68, 80)
        else:  # IDLE
            primary = QColor(148, 163, 184)    # Slate
            glow = QColor(148, 163, 184, 25)

        # Draw outer aura glow
        radius_glow = min(center_x, center_y) * (0.85 + 0.15 * pulse if self._state in (AppState.LISTENING, AppState.TRANSCRIBING) else 0.85)
        radial = QRadialGradient(center_x, center_y, radius_glow)
        radial.setColorAt(0.0, glow)
        radial.setColorAt(0.65, QColor(glow.red(), glow.green(), glow.blue(), int(glow.alpha() * 0.4)))
        radial.setColorAt(1.0, QColor(glow.red(), glow.green(), glow.blue(), 0))

        painter.setBrush(radial)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center_x - radius_glow, center_y - radius_glow, radius_glow * 2, radius_glow * 2)

        # Draw inner solid core
        core_radius = 4.2
        painter.setBrush(primary)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center_x - core_radius, center_y - core_radius, core_radius * 2, core_radius * 2)

"""Dynamic audio visualizer inspired by Apple visionOS liquid glass waveforms."""

import math
from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from models.app_state import AppState


class WaveformView(QWidget):
    """Smooth dynamic audio visualizer with multi-state animations.

    Renders vertical pill capsules with antialiased rendering, smooth lerp
    interpolation, breathing idle in PAUSED, and wave shimmer in TRANSCRIBING.
    """

    def __init__(self, parent: Optional[QWidget] = None, bar_count: int = 6):
        super().__init__(parent)
        self._bar_count = max(3, min(bar_count, 12))
        self._amplitude: float = 0.0
        self._target_amplitude: float = 0.0
        self._state: AppState = AppState.IDLE

        # Height multipliers for natural bell-curve envelope
        # e.g. for 6 bars: [0.35, 0.7, 1.0, 0.9, 0.6, 0.3]
        self._envelope = self._calculate_envelope(self._bar_count)

        # Current display heights (normalized 0.0 to 1.0)
        self._current_heights = [0.1] * self._bar_count
        self._target_heights = [0.1] * self._bar_count

        # Animation timer (approx 60 FPS = 16ms)
        self._phase: float = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

        self.setAttribute(Qt.WA_Hover, False)
        self.setMinimumSize(48, 20)

    @property
    def bar_count(self) -> int:
        return self._bar_count

    @property
    def amplitude(self) -> float:
        return self._amplitude

    @property
    def state(self) -> AppState:
        return self._state

    def _calculate_envelope(self, count: int) -> list[float]:
        """Calculates a smooth bell curve across the bars."""
        if count == 1:
            return [1.0]
        envelope = []
        center = (count - 1) / 2.0
        max_dist = max(center, 1.0)
        for i in range(count):
            dist = abs(i - center) / max_dist
            # Cosine-based tapering (1.0 at center, ~0.35 at edges)
            factor = 0.35 + 0.65 * math.cos(dist * (math.pi / 2.2))
            envelope.append(factor)
        return envelope

    def set_amplitude(self, amp: float) -> None:
        """Sets sound amplitude between 0.0 and 1.0."""
        self._amplitude = max(0.0, min(1.0, float(amp)))
        self._target_amplitude = self._amplitude

    def set_state(self, state: AppState) -> None:
        """Updates visual state and switches animation styles."""
        if self._state == state:
            return
        self._state = state
        if state == AppState.IDLE:
            self._amplitude = 0.0
            self._target_amplitude = 0.0
        self.update()

    def _on_tick(self) -> None:
        """Per-frame animation update step."""
        self._phase += 0.08
        if self._phase > 2 * math.pi * 100:
            self._phase = 0.0

        # Compute targets based on current state
        if self._state in (AppState.LISTENING, AppState.PASTING):
            # Dynamic audio response
            for i in range(self._bar_count):
                variation = 0.15 * math.sin(self._phase * 2.5 + i * 1.2)
                level = max(0.08, min(1.0, self._amplitude * self._envelope[i] + variation * self._amplitude))
                self._target_heights[i] = level

        elif self._state == AppState.PAUSED:
            # Subtle breathing pulse
            breath = 0.12 + 0.10 * (0.5 + 0.5 * math.sin(self._phase * 1.2))
            for i in range(self._bar_count):
                self._target_heights[i] = breath * self._envelope[i]

        elif self._state == AppState.TRANSCRIBING:
            # Traveling wave ripple shimmer
            for i in range(self._bar_count):
                wave = 0.2 + 0.45 * (0.5 + 0.5 * math.sin(self._phase * 2.0 + i * 0.9))
                self._target_heights[i] = wave

        elif self._state == AppState.DONE:
            # Gentle green contraction
            for i in range(self._bar_count):
                self._target_heights[i] = 0.25 * self._envelope[i]

        elif self._state == AppState.ERROR:
            # Flat low alert bars
            for i in range(self._bar_count):
                self._target_heights[i] = 0.18

        else:  # IDLE
            for i in range(self._bar_count):
                self._target_heights[i] = 0.08

        # Smooth lerp interpolation
        lerp_factor = 0.28
        changed = False
        for i in range(self._bar_count):
            prev = self._current_heights[i]
            target = self._target_heights[i]
            updated = prev + (target - prev) * lerp_factor
            if abs(updated - prev) > 0.001:
                changed = True
            self._current_heights[i] = updated

        if changed or self._state in (AppState.LISTENING, AppState.PAUSED, AppState.TRANSCRIBING):
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paints rounded vertical capsule bars with luminous styling."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        count = self._bar_count

        total_spacing = (count - 1) * 3
        bar_width = max(3.0, (w - total_spacing) / count)
        bar_width = min(bar_width, 6.0)

        # Total width occupied by bars
        drawn_width = count * bar_width + (count - 1) * 3
        start_x = (w - drawn_width) / 2.0
        center_y = h / 2.0

        for i in range(count):
            x = start_x + i * (bar_width + 3)
            # Minimum capsule height equals width for a nice circular dot when idle
            min_h = bar_width
            max_h = max(min_h, h * 0.9)
            norm_height = self._current_heights[i]
            bar_height = min_h + (max_h - min_h) * norm_height
            y = center_y - bar_height / 2.0

            # Color scheme depending on state
            gradient = QLinearGradient(x, y, x, y + bar_height)
            if self._state == AppState.LISTENING:
                # Electric cyan / neon blue
                gradient.setColorAt(0.0, QColor(0, 242, 254, 255))
                gradient.setColorAt(1.0, QColor(79, 172, 254, 220))
            elif self._state == AppState.PAUSED:
                # Translucent amber
                gradient.setColorAt(0.0, QColor(251, 191, 36, 240))
                gradient.setColorAt(1.0, QColor(217, 119, 6, 200))
            elif self._state == AppState.TRANSCRIBING:
                # Sky blue shimmer
                gradient.setColorAt(0.0, QColor(186, 230, 253, 255))
                gradient.setColorAt(1.0, QColor(56, 189, 248, 220))
            elif self._state == AppState.DONE:
                # Emerald green
                gradient.setColorAt(0.0, QColor(52, 211, 153, 255))
                gradient.setColorAt(1.0, QColor(16, 185, 129, 220))
            elif self._state == AppState.ERROR:
                # Red alert
                gradient.setColorAt(0.0, QColor(248, 113, 113, 255))
                gradient.setColorAt(1.0, QColor(239, 68, 68, 220))
            else:  # IDLE
                # Subtle slate
                gradient.setColorAt(0.0, QColor(148, 163, 184, 140))
                gradient.setColorAt(1.0, QColor(100, 116, 139, 100))

            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            radius = bar_width / 2.0
            painter.drawRoundedRect(x, y, bar_width, bar_height, radius, radius)

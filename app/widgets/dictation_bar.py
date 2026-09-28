"""Floating dictation bar container with visionOS liquid glass aesthetics."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.widgets.status_badge import StatusBadge
from app.widgets.waveform_view import WaveformView
from models.app_state import AppState


class DictationBar(QWidget):
    """Frosted dark glass pill container with visionOS styling, drop shadow,

    real-time waveform visualizer, and status indicators.
    """

    def __init__(self, parent: Optional[QWidget] = None, compact: bool = False):
        super().__init__(parent)
        self._is_compact = compact
        self._state = AppState.IDLE

        self._setup_ui()
        self._setup_shadow()
        self._apply_size_mode()

    @property
    def is_compact(self) -> bool:
        return self._is_compact

    @property
    def waveform(self) -> WaveformView:
        return self._waveform

    @property
    def badge(self) -> StatusBadge:
        return self._badge

    @property
    def title_label(self) -> QLabel:
        return self._title_label

    @property
    def subtitle_label(self) -> QLabel:
        return self._subtitle_label

    def _setup_ui(self) -> None:
        """Constructs layout, labels, badge, and waveform visualizer."""
        self.setAttribute(Qt.WA_Hover, False)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 10, 18, 10)
        main_layout.setSpacing(14)

        # Status badge (Left)
        self._badge = StatusBadge(self)
        main_layout.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignVCenter)

        # Center text column (Title + Subtitle)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self._title_label = QLabel("Listo para dictar", self)
        title_font = QFont("Segoe UI", 11)
        title_font.setWeight(QFont.Weight.DemiBold)
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet("color: #F8FAFC; background: transparent;")

        self._subtitle_label = QLabel("Presiona el atajo para comenzar", self)
        sub_font = QFont("Segoe UI", 9)
        sub_font.setWeight(QFont.Weight.Normal)
        self._subtitle_label.setFont(sub_font)
        self._subtitle_label.setStyleSheet("color: #94A3B8; background: transparent;")

        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._subtitle_label)
        main_layout.addLayout(text_layout, 1)

        # Waveform visualizer (Right)
        self._waveform = WaveformView(self, bar_count=6)
        self._waveform.setFixedSize(58, 28)
        main_layout.addWidget(self._waveform, 0, Qt.AlignmentFlag.AlignVCenter)

    def _setup_shadow(self) -> None:
        """Attaches deep diffuse drop shadow."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 175))
        self.setGraphicsEffect(shadow)

    def _apply_size_mode(self) -> None:
        """Updates geometry and internal paddings based on compact mode."""
        layout = self.layout()
        if self._is_compact:
            self.setFixedSize(380, 56)
            if layout:
                layout.setContentsMargins(14, 6, 14, 6)
                layout.setSpacing(10)
            self._title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            self._subtitle_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal))
            self._waveform.setFixedSize(48, 22)
        else:
            self.setFixedSize(460, 70)
            if layout:
                layout.setContentsMargins(20, 10, 20, 10)
                layout.setSpacing(14)
            self._title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            self._subtitle_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
            self._waveform.setFixedSize(60, 28)

    def set_compact(self, compact: bool) -> None:
        """Toggles between normal and compact layout dimensions."""
        if self._is_compact == compact:
            return
        self._is_compact = compact
        self._apply_size_mode()
        self.update()

    def set_title(self, text: str) -> None:
        """Sets the primary title display text."""
        self._title_label.setText(text)

    def set_subtitle(self, text: str) -> None:
        """Sets the secondary helper or status subtitle."""
        self._subtitle_label.setText(text)

    def set_state(self, state: AppState) -> None:
        """Propagates state to badge and waveform."""
        self._state = state
        self._badge.set_state(state)
        self._waveform.set_state(state)
        self.update()

    def set_amplitude(self, amp: float) -> None:
        """Forwards audio amplitude to the waveform visualizer."""
        self._waveform.set_amplitude(amp)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paints liquid glass background and subtle illuminated border highlight."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = 24.0 if not self._is_compact else 18.0

        # Dark translucent frosted glass background: rgba(20, 24, 36, 0.88)
        glass_bg = QColor(20, 24, 36, 225)
        painter.setBrush(glass_bg)

        # Illuminated border with subtle top-lit gradient: rgba(255, 255, 255, 0.22) -> rgba(255, 255, 255, 0.08)
        border_grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        border_grad.setColorAt(0.0, QColor(255, 255, 255, 55))
        border_grad.setColorAt(0.6, QColor(255, 255, 255, 25))
        border_grad.setColorAt(1.0, QColor(255, 255, 255, 12))

        pen = QPen(border_grad, 1.2)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, radius, radius)

"""visionOS inspired floating overlay with liquid glass styling and Win32 no-activate support."""

import sys
from typing import Optional
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent, QShowEvent
from PySide6.QtWidgets import QHBoxLayout, QWidget

from app.widgets.dictation_bar import DictationBar
from controllers.dictation_controller import DictationController
from models.app_state import AppState
from utils.config import ConfigManager
from utils.logger import get_logger

logger = get_logger("app.overlay")

# Win32 Constants for non-activating window
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000


class FloatingOverlay(QWidget):
    """Floating transparent overlay window.

    Guarantees no focus stealing from active apps (Word, Chrome, VS Code) using
    WS_EX_NOACTIVATE on Windows. Supports smooth fade-in/out animations, Esc to cancel,
    and responsive positioning.
    """

    def __init__(
        self,
        controller: DictationController,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._controller = controller
        self._config_manager = config_manager or ConfigManager()

        self._fade_animation: Optional[QPropertyAnimation] = None

        self._setup_window_flags()
        self._setup_ui()
        self._connect_signals()
        self.apply_config_settings()

    @property
    def dictation_bar(self) -> DictationBar:
        return self._dictation_bar

    @property
    def fade_animation(self) -> Optional[QPropertyAnimation]:
        return self._fade_animation

    def _setup_window_flags(self) -> None:
        """Sets frameless, always-on-top, tool, and no-focus window flags."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def _setup_ui(self) -> None:
        """Embeds DictationBar inside a padded layout to accommodate drop shadow."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        self._dictation_bar = DictationBar(self)
        layout.addWidget(self._dictation_bar)

    def _apply_win32_noactivate(self) -> None:
        """Applies WS_EX_NOACTIVATE on Windows to ensure active apps keep focus."""
        if sys.platform != "win32":
            return

        try:
            import ctypes
            from ctypes import wintypes

            hwnd = int(self.winId())
            if not hwnd:
                return

            if hasattr(ctypes.windll.user32, "GetWindowLongPtrW"):
                get_window_long = ctypes.windll.user32.GetWindowLongPtrW
                set_window_long = ctypes.windll.user32.SetWindowLongPtrW
                get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
                get_window_long.restype = ctypes.c_longlong
                set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
                set_window_long.restype = ctypes.c_longlong
            else:
                get_window_long = ctypes.windll.user32.GetWindowLongW
                set_window_long = ctypes.windll.user32.SetWindowLongW
                get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
                get_window_long.restype = ctypes.c_long
                set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
                set_window_long.restype = ctypes.c_long

            current_style = get_window_long(hwnd, GWL_EXSTYLE)
            if not (current_style & WS_EX_NOACTIVATE):
                set_window_long(hwnd, GWL_EXSTYLE, current_style | WS_EX_NOACTIVATE)
                logger.debug("Applied WS_EX_NOACTIVATE to FloatingOverlay HWND")
        except Exception as e:
            logger.warning(f"Could not apply WS_EX_NOACTIVATE: {e}")

    def showEvent(self, event: QShowEvent) -> None:
        """Ensures win32 styles are applied whenever window is shown."""
        super().showEvent(event)
        self._apply_win32_noactivate()

    def _connect_signals(self) -> None:
        """Binds controller signals to overlay updates."""
        if self._controller is not None:
            self._controller.state_changed.connect(self._on_state_changed)
            self._controller.amplitude_updated.connect(self._on_amplitude_updated)
            self._controller.status_text_updated.connect(self._on_status_text_updated)
            self._controller.subtext_updated.connect(self._on_subtext_updated)

    def apply_config_settings(self) -> None:
        """Applies configured size mode and repositions."""
        size_mode = self._config_manager.get_overlay_size()
        is_compact = size_mode.lower() == "compact"
        self._dictation_bar.set_compact(is_compact)
        self.adjustSize()
        self.reposition()

    def reposition(self) -> None:
        """Positions overlay centered horizontally, top or bottom of primary screen."""
        self.adjustSize()
        screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        overlay_w = self.width()
        overlay_h = self.height()

        x = screen_geo.left() + (screen_geo.width() - overlay_w) // 2

        pos = self._config_manager.get_overlay_position()
        if pos.lower() == "bottom":
            y = screen_geo.bottom() - overlay_h - 80
        else:  # "top"
            y = screen_geo.top() + 60

        self.move(x, y)

    def _on_state_changed(self, state: AppState) -> None:
        """Handles session state transitions."""
        self._dictation_bar.set_state(state)
        if state == AppState.IDLE:
            self.hide_overlay()
        else:
            self.show_overlay()

    def _on_amplitude_updated(self, amp: float) -> None:
        """Updates waveform visualizer amplitude."""
        self._dictation_bar.set_amplitude(amp)

    def _on_status_text_updated(self, text: str) -> None:
        """Updates main title text."""
        self._dictation_bar.set_title(text)

    def _on_subtext_updated(self, text: str) -> None:
        """Updates secondary subtitle text."""
        self._dictation_bar.set_subtitle(text)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Cancels dictation on Escape key press."""
        if event.key() == Qt.Key.Key_Escape:
            logger.info("Escape pressed in FloatingOverlay: canceling dictation.")
            if self._controller is not None:
                self._controller.cancel_dictation()
            event.accept()
            return
        super().keyPressEvent(event)

    def show_overlay(self) -> None:
        """Displays overlay with smooth fade-in animation."""
        self.reposition()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()

        if self._fade_animation is not None and self._fade_animation.state() == QPropertyAnimation.State.Running:
            self._fade_animation.stop()

        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(220)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_animation = anim
        anim.start()

    def hide_overlay(self) -> None:
        """Fades out overlay and hides upon completion."""
        if not self.isVisible():
            return

        if self._fade_animation is not None and self._fade_animation.state() == QPropertyAnimation.State.Running:
            self._fade_animation.stop()

        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(200)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def _on_finished() -> None:
            if self.windowOpacity() == 0.0:
                self.hide()

        anim.finished.connect(_on_finished)
        self._fade_animation = anim
        anim.start()

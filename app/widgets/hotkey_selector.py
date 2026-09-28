"""
HotkeySelector Widget
Interactive, visionOS/liquid glass styled widget for selecting and validating global hotkeys.
"""

from typing import Optional, List
from PySide6.QtCore import Qt, Signal, QObject, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)

from utils.config import ConfigManager, DEFAULT_HOTKEY
from utils.logger import get_logger
from input.hotkey_manager import HotkeyManager, MODIFIER_ORDER

logger = get_logger("VoiceDictation.HotkeySelector")

try:
    from pynput import keyboard as pynput_keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


# VisionOS / Liquid Glass Stylesheets
CONTAINER_STYLE = """
QFrame#selector_container {
    background-color: rgba(28, 28, 32, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 12px;
}
"""

BADGE_STYLE = """
QLabel {
    background-color: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 6px;
    color: #FFFFFF;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
    font-size: 13px;
    font-weight: 600;
    padding: 5px 12px;
}
"""

PLUS_STYLE = """
QLabel {
    color: rgba(255, 255, 255, 0.45);
    font-size: 14px;
    font-weight: 700;
    padding: 0 4px;
}
"""

CAPTURE_NORMAL_STYLE = """
QPushButton#capture_button {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
    color: #F5F5F7;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 18px;
    text-align: center;
}
QPushButton#capture_button:hover {
    background-color: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.28);
}
"""

CAPTURE_ACTIVE_STYLE = """
QPushButton#capture_button {
    background-color: rgba(10, 132, 255, 0.18);
    border: 2px solid #0A84FF;
    border-radius: 10px;
    color: #64D2FF;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 18px;
    text-align: center;
}
"""

SAVE_BUTTON_STYLE = """
QPushButton#save_button {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0A84FF, stop:1 #0071E3);
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 7px 18px;
}
QPushButton#save_button:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #409CFF, stop:1 #0A84FF);
}
QPushButton#save_button:disabled {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.3);
}
"""

RESTORE_BUTTON_STYLE = """
QPushButton#restore_button {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.85);
    font-size: 12px;
    font-weight: 500;
    padding: 7px 14px;
}
QPushButton#restore_button:hover {
    background-color: rgba(255, 255, 255, 0.12);
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.3);
}
"""

FEEDBACK_STYLE_NORMAL = "color: rgba(255, 255, 255, 0.7); font-size: 12px;"
FEEDBACK_STYLE_SUCCESS = "color: #30D158; font-size: 12px; font-weight: 500;"
FEEDBACK_STYLE_WARNING = "color: #FF9F0A; font-size: 12px; font-weight: 500;"
FEEDBACK_STYLE_ERROR = "color: #FF453A; font-size: 12px; font-weight: 500;"


class HotkeySelector(QWidget):
    """
    Physical Hotkey Selector widget adhering to visionOS aesthetic.
    Allows capturing keyboard combinations, validating them, showing visual badges,
    and persisting user changes.
    """

    hotkey_saved = Signal(str)
    capture_cancelled = Signal()

    def __init__(
        self,
        hotkey_manager: Optional[HotkeyManager] = None,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._config_manager = config_manager or ConfigManager()
        self._hotkey_manager = hotkey_manager
        if self._hotkey_manager is None:
            try:
                self._hotkey_manager = HotkeyManager(config_manager=self._config_manager)
            except Exception as e:
                logger.warning(f"Could not auto-instantiate HotkeyManager: {e}")
                self._hotkey_manager = None

        mgr_key = ""
        if (
            self._hotkey_manager
            and hasattr(self._hotkey_manager, "get_current_hotkey")
            and callable(self._hotkey_manager.get_current_hotkey)
        ):
            try:
                mgr_key = self._hotkey_manager.get_current_hotkey() or ""
            except Exception:
                mgr_key = ""

        self._current_hotkey = mgr_key or self._config_manager.get_hotkey() or DEFAULT_HOTKEY
        self._candidate_hotkey = self._current_hotkey
        self._is_capturing = False
        self._pynput_listener = None

        self._init_ui()
        self._update_badges(self._current_hotkey)
        self._update_display_text()

    def _init_ui(self) -> None:
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Glass Container Frame
        self._container = QFrame(self)
        self._container.setObjectName("selector_container")
        self._container.setStyleSheet(CONTAINER_STYLE)
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(14, 14, 14, 14)
        container_layout.setSpacing(12)

        # Title Label
        title_label = QLabel("Combinación de teclas para dictado:")
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-size: 13px; font-weight: 600;")
        container_layout.addWidget(title_label)

        # Visual Badges Container
        self.badges_container = QWidget(self._container)
        self._badges_layout = QHBoxLayout(self.badges_container)
        self._badges_layout.setContentsMargins(0, 4, 0, 4)
        self._badges_layout.setSpacing(6)
        self._badges_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        container_layout.addWidget(self.badges_container)

        # Interactive Capture Button
        self.capture_button = QPushButton(self._container)
        self.capture_button.setObjectName("capture_button")
        self.capture_button.setStyleSheet(CAPTURE_NORMAL_STYLE)
        self.capture_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.capture_button.clicked.connect(self._on_capture_button_clicked)
        container_layout.addWidget(self.capture_button)

        # Feedback / Error / Warning Label
        self.feedback_label = QLabel(self._container)
        self.feedback_label.setStyleSheet(FEEDBACK_STYLE_NORMAL)
        self.feedback_label.setWordWrap(True)
        container_layout.addWidget(self.feedback_label)

        # Buttons Row (Restore Default + Save)
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 4, 0, 0)
        buttons_layout.setSpacing(10)

        self.restore_button = QPushButton("Restaurar combinación recomendada", self._container)
        self.restore_button.setObjectName("restore_button")
        self.restore_button.setStyleSheet(RESTORE_BUTTON_STYLE)
        self.restore_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_button.clicked.connect(self.restore_default)
        buttons_layout.addWidget(self.restore_button)

        buttons_layout.addStretch()

        self.save_button = QPushButton("Guardar", self._container)
        self.save_button.setObjectName("save_button")
        self.save_button.setStyleSheet(SAVE_BUTTON_STYLE)
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_hotkey)
        buttons_layout.addWidget(self.save_button)

        container_layout.addLayout(buttons_layout)
        main_layout.addWidget(self._container)

    def _update_badges(self, hotkey_str: str) -> None:
        """Clears and rebuilds the visual badges corresponding to the hotkey string."""
        # Clear existing widgets in badges layout
        while self._badges_layout.count():
            item = self._badges_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not hotkey_str:
            return

        parts = [p.strip() for p in hotkey_str.split("+") if p.strip()]
        for idx, part in enumerate(parts):
            badge = QLabel(part)
            badge.setStyleSheet(BADGE_STYLE)
            self._badges_layout.addWidget(badge)

            if idx < len(parts) - 1:
                plus = QLabel("+")
                plus.setStyleSheet(PLUS_STYLE)
                self._badges_layout.addWidget(plus)

    def _update_display_text(self) -> None:
        """Updates the text on the interactive capture button and display."""
        if self._is_capturing:
            self.capture_button.setText("Presiona la nueva combinación...")
            self.capture_button.setStyleSheet(CAPTURE_ACTIVE_STYLE)
        else:
            active = self._candidate_hotkey or self._current_hotkey
            formatted = " + ".join([p.strip() for p in active.split("+") if p.strip()])
            self.capture_button.setText(f"{formatted}  (Clic para cambiar)")
            self.capture_button.setStyleSheet(CAPTURE_NORMAL_STYLE)

    def get_display_text(self) -> str:
        """Returns the formatted representation of the current/candidate hotkey."""
        active = self._candidate_hotkey or self._current_hotkey
        return " + ".join([p.strip() for p in active.split("+") if p.strip()])

    def get_current_hotkey(self) -> str:
        return self._current_hotkey

    def get_candidate_hotkey(self) -> str:
        return self._candidate_hotkey

    def is_capturing(self) -> bool:
        return self._is_capturing

    def _on_capture_button_clicked(self) -> None:
        if self._is_capturing:
            self.cancel_capture()
        else:
            self.start_capture()

    def start_capture(self) -> None:
        """Enters hotkey capture mode."""
        self._is_capturing = True
        self._update_display_text()
        self.set_feedback("Presiona las teclas de la combinación (Esc para cancelar)...", level="normal")
        self.setFocus()
        try:
            self.grabKeyboard()
        except Exception:
            pass

        # Optional pynput listener fallback
        if PYNPUT_AVAILABLE and not self._pynput_listener:
            try:
                self._pynput_listener = pynput_keyboard.Listener(
                    on_press=self._on_pynput_press
                )
                self._pynput_listener.daemon = True
                self._pynput_listener.start()
            except Exception as e:
                logger.debug(f"Pynput listener fallback could not be started: {e}")
                self._pynput_listener = None

    def cancel_capture(self) -> None:
        """Cancels capture mode and restores previous state."""
        self._stop_capture_mode()
        self._candidate_hotkey = self._current_hotkey
        self._update_badges(self._current_hotkey)
        self._update_display_text()
        self.set_feedback("", level="normal")
        self.save_button.setEnabled(False)
        self.capture_cancelled.emit()

    def _stop_capture_mode(self) -> None:
        """Internal cleanup when leaving capture mode."""
        self._is_capturing = False
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        if self._pynput_listener:
            try:
                self._pynput_listener.stop()
            except Exception:
                pass
            self._pynput_listener = None

    def _finish_capture(self, candidate: str) -> None:
        """Called when a full key combination has been captured."""
        self._stop_capture_mode()
        self._candidate_hotkey = candidate
        self._update_badges(candidate)
        self._update_display_text()
        self.validate_candidate(candidate)

    def validate_candidate(self, candidate: str) -> bool:
        """
        Validates candidate hotkey:
        1. Checks syntax / modifiers using HotkeyManager.validate_hotkey
        2. Checks availability using HotkeyManager.is_hotkey_available
        3. Updates feedback message and save_button state
        """
        if not candidate:
            self.set_feedback("El atajo no puede estar vacío.", level="warning")
            self.save_button.setEnabled(False)
            return False

        if self._hotkey_manager:
            is_valid, validation_msg = self._hotkey_manager.validate_hotkey(candidate)
        else:
            is_valid, validation_msg = HotkeyManager.validate_hotkey(candidate)

        if not is_valid:
            msg = validation_msg
            if "modificador" in validation_msg.lower() or "alfanum" in validation_msg.lower() or "funci" in validation_msg.lower():
                msg = "La combinación debe incluir al menos una tecla modificadora (Ctrl, Alt, Shift)."
            self.set_feedback(msg, level="warning")
            self.save_button.setEnabled(False)
            return False

        # Test availability
        if self._hotkey_manager and hasattr(self._hotkey_manager, "is_hotkey_available"):
            is_available, avail_msg = self._hotkey_manager.is_hotkey_available(candidate)
            if not is_available:
                self.set_feedback(avail_msg, level="error")
                self.save_button.setEnabled(False)
                return False

        # Check if identical to currently active registered key
        if candidate == self._current_hotkey:
            self.set_feedback("Combinación actual ya configurada.", level="normal")
            self.save_button.setEnabled(False)
        else:
            self.set_feedback("Combinación válida y disponible.", level="success")
            self.save_button.setEnabled(True)

        return True

    def set_feedback(self, text: str, level: str = "normal") -> None:
        """Sets the feedback label text with appropriate color theme."""
        self.feedback_label.setText(text)
        if level == "error":
            self.feedback_label.setStyleSheet(FEEDBACK_STYLE_ERROR)
        elif level == "warning":
            self.feedback_label.setStyleSheet(FEEDBACK_STYLE_WARNING)
        elif level == "success":
            self.feedback_label.setStyleSheet(FEEDBACK_STYLE_SUCCESS)
        else:
            self.feedback_label.setStyleSheet(FEEDBACK_STYLE_NORMAL)

    def save_hotkey(self) -> None:
        """Persists the candidate hotkey and registers it."""
        if not self._candidate_hotkey:
            return

        if self._hotkey_manager:
            success, msg = self._hotkey_manager.register_hotkey(self._candidate_hotkey)
            if not success:
                self.set_feedback(msg, level="error")
                self.save_button.setEnabled(False)
                return

        self._current_hotkey = self._candidate_hotkey
        self._config_manager.set_hotkey(self._current_hotkey)
        self.save_button.setEnabled(False)
        self.set_feedback(f"Combinación guardada con éxito: {self._current_hotkey}", level="success")
        self._update_display_text()
        self.hotkey_saved.emit(self._current_hotkey)

    def restore_default(self) -> None:
        """Restores the recommended default hotkey (Ctrl+Space)."""
        if self._is_capturing:
            self._stop_capture_mode()

        candidate = DEFAULT_HOTKEY
        self._candidate_hotkey = candidate
        self._update_badges(candidate)
        self._update_display_text()
        self.validate_candidate(candidate)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Intercepts keyboard events during capture mode."""
        if not self._is_capturing:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        # Escape without modifiers cancels capture
        if key == Qt.Key.Key_Escape and modifiers == Qt.KeyboardModifier.NoModifier:
            self.cancel_capture()
            return

        # Extract modifier components
        mods: List[str] = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            mods.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            mods.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            mods.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            mods.append("Win")

        # Check if the pressed key is a modifier itself
        if key in (
            Qt.Key.Key_Control,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Meta,
        ):
            # Modifier held down, show visual badge progress
            if mods:
                preview = "+".join(mods)
                self._update_badges(preview)
            return

        # Map base key
        base_key = self._map_qt_key(key, event.text())

        if not base_key:
            return

        parts = mods + [base_key]
        candidate = "+".join(parts)
        normalized = HotkeyManager.normalize_hotkey(candidate)
        self._finish_capture(normalized or candidate)

    def _map_qt_key(self, key: int, text: str) -> str:
        """Maps Qt key codes to canonical hotkey strings."""
        if key == Qt.Key.Key_Space:
            return "Space"
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return "Enter"
        if key == Qt.Key.Key_Tab:
            return "Tab"
        if key == Qt.Key.Key_Backspace:
            return "Backspace"
        if key == Qt.Key.Key_Delete:
            return "Delete"
        if key == Qt.Key.Key_Insert:
            return "Insert"
        if key == Qt.Key.Key_Home:
            return "Home"
        if key == Qt.Key.Key_End:
            return "End"
        if key == Qt.Key.Key_PageUp:
            return "PageUp"
        if key == Qt.Key.Key_PageDown:
            return "PageDown"
        if key == Qt.Key.Key_Up:
            return "Up"
        if key == Qt.Key.Key_Down:
            return "Down"
        if key == Qt.Key.Key_Left:
            return "Left"
        if key == Qt.Key.Key_Right:
            return "Right"
        if key == Qt.Key.Key_Escape:
            return "Esc"

        # Function keys F1-F24
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
            return f"F{key - Qt.Key.Key_F1 + 1}"

        # Alphanumeric text
        if text and text.strip() and text.isprintable():
            return text.strip().upper()

        # Fallback to key code ASCII
        if 0x20 <= key <= 0x7E:
            return chr(key).upper()

        return ""

    def _on_pynput_press(self, key) -> None:
        """Pynput background listener callback (used if window loses focus)."""
        # Only process if window is inactive and capturing is on
        if not self._is_capturing or self.isActiveWindow():
            return

        # We can handle external capture if needed
        # In general, Qt key events handle 100% of focused interaction
        pass

    def closeEvent(self, event) -> None:
        """Clean up background threads on close."""
        self._stop_capture_mode()
        super().closeEvent(event)

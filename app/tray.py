"""System Tray Icon and context menu for Voice Dictation."""

from typing import Optional, Callable
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
    QWidget,
    QApplication,
)

from controllers.dictation_controller import DictationController
from models.app_state import AppState
from utils.logger import get_logger

logger = get_logger("app.tray")


def create_default_tray_icon() -> QIcon:
    """Generates a high-DPI modern microphone/wave icon for the system tray."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Gradient background circle (subtle blue/cyan glow)
    circle_color = QColor(10, 132, 255, 230)
    painter.setBrush(circle_color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, size - 8, size - 8, 16, 16)

    # Draw microphone icon in white
    pen = QPen(QColor(255, 255, 255), 3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QColor(255, 255, 255))

    # Mic capsule
    painter.drawRoundedRect(24, 14, 16, 24, 8, 8)

    # Mic cup/arc
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(18, 22, 28, 22, 0, -180 * 16)

    # Mic stand line & base
    painter.drawLine(32, 44, 32, 51)
    painter.drawLine(24, 51, 40, 51)

    painter.end()
    return QIcon(pixmap)


class SystemTrayIcon(QSystemTrayIcon):
    """Windows system tray icon with dynamic context menu and lifecycle hooks."""

    open_settings_requested = Signal(str)  # Tab name: "general", "dictation", "appearance", "about"
    toggle_dictation_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self,
        controller: Optional[DictationController] = None,
        parent: Optional[QWidget] = None,
        on_open_settings: Optional[Callable[[str], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self._controller = controller
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit

        self.setIcon(create_default_tray_icon())
        self.setToolTip("Voice Dictation - Dictado por Voz")

        self._setup_menu()
        self._connect_signals()

    def _setup_menu(self) -> None:
        """Constructs the system tray context menu."""
        self._menu = QMenu()
        self._menu.setStyleSheet(
            """
            QMenu {
                background-color: rgba(30, 30, 35, 0.95);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 24px 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0A84FF;
                color: #FFFFFF;
            }
            QMenu::item:disabled {
                color: rgba(255, 255, 255, 0.4);
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.12);
                margin: 4px 6px;
            }
            """
        )

        # Title Item (Disabled info header)
        self._title_action = self._menu.addAction("Voice Dictation")
        self._title_action.setEnabled(False)
        font = self._title_action.font()
        font.setBold(True)
        self._title_action.setFont(font)

        # Dynamic Dictation Toggle Action
        hotkey = self._get_current_hotkey()
        self._dictation_action = self._menu.addAction(f"Iniciar dictado      [{hotkey}]")
        self._dictation_action.triggered.connect(self._on_toggle_dictation)

        self._menu.addSeparator()

        # Settings Actions
        self._settings_action = self._menu.addAction("Configuración...")
        self._settings_action.triggered.connect(lambda: self.open_settings("general"))

        self._change_hotkey_action = self._menu.addAction("Cambiar atajo...")
        self._change_hotkey_action.triggered.connect(lambda: self.open_settings("dictation"))

        self._about_action = self._menu.addAction("Acerca de...")
        self._about_action.triggered.connect(self.show_about_dialog)

        self._menu.addSeparator()

        # Quit Action
        self._quit_action = self._menu.addAction("Salir")
        self._quit_action.triggered.connect(self._on_quit_triggered)

        self.setContextMenu(self._menu)

    def _connect_signals(self) -> None:
        """Connects tray activation and controller signals."""
        self.activated.connect(self._on_tray_activated)

        if self._controller is not None:
            self._controller.hotkey_updated.connect(self.update_hotkey_text)
            self._controller.state_changed.connect(self._on_controller_state_changed)

    def _get_current_hotkey(self) -> str:
        if self._controller is not None:
            return self._controller.current_hotkey
        return "Ctrl+Space"

    def update_hotkey_text(self, hotkey: str) -> None:
        """Dynamically updates the menu action with the latest hotkey."""
        is_active = (
            self._controller is not None
            and self._controller.state in (AppState.LISTENING, AppState.PAUSED)
        )
        action_verb = "Detener dictado" if is_active else "Iniciar dictado"
        self._dictation_action.setText(f"{action_verb}      [{hotkey}]")

    def _on_controller_state_changed(self, state: AppState) -> None:
        """Updates menu text and tooltip according to session state."""
        hotkey = self._get_current_hotkey()
        if state in (AppState.LISTENING, AppState.PAUSED):
            self._dictation_action.setText(f"Detener dictado      [{hotkey}]")
            self.setToolTip("Voice Dictation - Escuchando...")
        else:
            self._dictation_action.setText(f"Iniciar dictado      [{hotkey}]")
            self.setToolTip("Voice Dictation - En espera")

    def _on_toggle_dictation(self) -> None:
        """Invoked when the user triggers the dictation menu action."""
        if self._controller is not None:
            self._controller.toggle_dictation()
        self.toggle_dictation_requested.emit()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handles user clicking the system tray icon."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click toggles dictation
            if self._controller is not None:
                self._controller.toggle_dictation()
            self.toggle_dictation_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click opens settings
            self.open_settings("general")

    def open_settings(self, tab: str = "general") -> None:
        """Requests opening settings at a specific tab."""
        logger.debug(f"Opening settings tab: {tab}")
        self.open_settings_requested.emit(tab)
        if self._on_open_settings is not None:
            self._on_open_settings(tab)

    def show_about_dialog(self) -> None:
        """Displays the 'Acerca de Voice Dictation' dialog modal."""
        about_box = QMessageBox()
        about_box.setWindowTitle("Acerca de Voice Dictation")
        about_box.setIcon(QMessageBox.Icon.Information)
        about_box.setText(
            "<h3>Voice Dictation</h3>"
            "<p><b>Versión:</b> v1.0.0</p>"
            "<p>Utility de dictado global para Windows con transcripción local y activación mediante atajos personalizables.</p>"
            "<p><b>Desarrollado por:</b> David Caro (<a href='https://instagram.com/ing.davidcaro' style='color: #0A84FF;'>@ing.davidcaro</a>)</p>"
            "<hr>"
            "<p style='color: #8E8E93; font-size: 11px;'>100% Local • Privacidad Total • faster-whisper</p>"
        )
        about_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        about_box.exec()

    def _on_quit_triggered(self) -> None:
        """Initiates graceful application exit."""
        logger.info("Quit triggered from system tray.")
        self.quit_requested.emit()
        if self._on_quit is not None:
            self._on_quit()
        else:
            if self._controller is not None:
                self._controller.cleanup()
            app = QApplication.instance()
            if app is not None:
                app.quit()

"""Main Application Coordinator and Lifecycle Manager for Voice Dictation."""

import sys
from typing import Optional
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication, QWidget

from app.first_run import FirstRunWizard
from app.overlay import FloatingOverlay
from app.settings_window import SettingsWindow
from app.tray import SystemTrayIcon
from audio.recorder import AudioRecorder
from controllers.dictation_controller import DictationController
from input.clipboard import Clipboard
from input.hotkey_manager import HotkeyManager
from input.paste import Paster
from speech.model_manager import ModelManager
from utils.config import ConfigManager
from utils.logger import get_logger

logger = get_logger("app.main_window")


class MainWindow(QObject):
    """Coordinates lifecycle, system tray, floating overlay, settings, and first-run onboarding."""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        hotkey_manager: Optional[HotkeyManager] = None,
        audio_recorder: Optional[AudioRecorder] = None,
        clipboard: Optional[Clipboard] = None,
        paster: Optional[Paster] = None,
        model_manager: Optional[ModelManager] = None,
        controller: Optional[DictationController] = None,
        overlay: Optional[FloatingOverlay] = None,
        tray: Optional[SystemTrayIcon] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._config_manager = config_manager or ConfigManager()
        self._hotkey_manager = hotkey_manager or HotkeyManager(config_manager=self._config_manager)
        self._audio_recorder = audio_recorder or AudioRecorder()
        self._clipboard = clipboard or Clipboard()
        self._paster = paster or Paster()
        self._model_manager = model_manager or ModelManager()

        # Session Controller
        self._controller = controller or DictationController(
            config_manager=self._config_manager,
            hotkey_manager=self._hotkey_manager,
            audio_recorder=self._audio_recorder,
            clipboard=self._clipboard,
            paster=self._paster,
            model_manager=self._model_manager,
            parent=self,
        )

        # UI Components
        self._overlay = overlay or FloatingOverlay(
            controller=self._controller,
            config_manager=self._config_manager,
        )

        self._tray = tray or SystemTrayIcon(
            controller=self._controller,
            on_open_settings=self.open_settings,
            on_quit=self.quit,
            parent=None,
        )

        self._settings_window: Optional[SettingsWindow] = None
        self._first_run_wizard: Optional[FirstRunWizard] = None

        self._connect_signals()

    @property
    def controller(self) -> DictationController:
        return self._controller

    @property
    def overlay(self) -> FloatingOverlay:
        return self._overlay

    @property
    def tray(self) -> SystemTrayIcon:
        return self._tray

    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager

    @property
    def hotkey_manager(self) -> HotkeyManager:
        return self._hotkey_manager

    def _connect_signals(self) -> None:
        """Connects tray and controller signals."""
        self._tray.open_settings_requested.connect(self.open_settings)
        self._tray.quit_requested.connect(self.quit)
        self._controller.hotkey_updated.connect(self._on_hotkey_updated)

    def _on_hotkey_updated(self, new_hotkey: str) -> None:
        """Propagates hotkey updates to tray and overlay."""
        self._tray.update_hotkey_text(new_hotkey)
        self._overlay.apply_config_settings()

    def start(self) -> None:
        """Starts the application services and system tray."""
        logger.info("Starting Voice Dictation application...")

        # Pre-warm Whisper model in background
        self._start_model_warmup()

        # Show tray icon
        self._tray.show()

        # Check for first run
        if self._config_manager.is_first_run():
            logger.info("First run detected. Displaying FirstRunWizard.")
            self.show_first_run()
        else:
            # Register initial hotkey
            hotkey = self._config_manager.get_hotkey()
            success, msg = self._hotkey_manager.register_hotkey(hotkey)
            if not success:
                logger.warning(f"Could not register startup hotkey '{hotkey}': {msg}")

    def _start_model_warmup(self) -> None:
        """Triggers background pre-warming of the configured Whisper model."""
        if self._model_manager is not None:
            model_name = self._config_manager.get_model_name()
            self._model_manager.preload_model_async(model_name=model_name)

    def show_first_run(self) -> None:
        """Displays the first-run onboarding dialog."""
        wizard = FirstRunWizard(
            config_manager=self._config_manager,
            hotkey_manager=self._hotkey_manager,
        )
        self._first_run_wizard = wizard
        wizard.finished.connect(self._on_first_run_finished)
        wizard.show()
        wizard.raise_()
        wizard.activateWindow()

    def _on_first_run_finished(self) -> None:
        """Handles completion of onboarding wizard."""
        hotkey = self._config_manager.get_hotkey()
        if not self._hotkey_manager.is_registered():
            success, msg = self._hotkey_manager.register_hotkey(hotkey)
            if not success:
                logger.warning(f"Could not register hotkey after onboarding: {msg}")
        self._tray.update_hotkey_text(hotkey)
        self._overlay.apply_config_settings()

    def open_settings(self, tab: str = "general") -> None:
        """Opens or brings the settings window to the foreground at the requested tab."""
        if self._settings_window is None:
            self._settings_window = SettingsWindow(
                config_manager=self._config_manager,
                hotkey_manager=self._hotkey_manager,
            )
            self._settings_window.settings_updated.connect(self._on_settings_updated)

        self._settings_window.select_tab(tab)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()

    def _on_settings_updated(self) -> None:
        """Applies configuration changes across components."""
        self._overlay.apply_config_settings()
        hotkey = self._config_manager.get_hotkey()
        self._tray.update_hotkey_text(hotkey)

    def quit(self) -> None:
        """Gracefully shuts down all workers, hooks, and terminates the application."""
        logger.info("Graceful application shutdown initiated.")
        if self._controller is not None:
            self._controller.cleanup()

        if self._settings_window is not None:
            self._settings_window.close()

        if self._first_run_wizard is not None:
            self._first_run_wizard.close()

        if self._overlay is not None:
            self._overlay.close()

        if self._tray is not None:
            self._tray.hide()

        app = QApplication.instance()
        if app is not None:
            app.quit()


# Alias for compatibility
VoiceDictationApp = MainWindow

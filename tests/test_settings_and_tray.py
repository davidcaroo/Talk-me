"""Unit and integration tests for Settings, FirstRunWizard, SystemTrayIcon, and Main Coordinator."""

import sys
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtCore import QSettings, Qt, QObject, Signal
from PySide6.QtWidgets import QApplication

from app.first_run import FirstRunWizard
from app.main_window import MainWindow
from app.settings_window import SettingsWindow
from app.tray import SystemTrayIcon, create_default_tray_icon
from audio.recorder import AudioRecorder
from controllers.dictation_controller import DictationController
from input.clipboard import Clipboard
from input.hotkey_manager import HotkeyManager
from input.paste import Paster
from models.app_state import AppState
from utils.config import ConfigManager
from utils.startup import (
    APP_NAME,
    RUN_KEY_PATH,
    get_app_command,
    is_startup_enabled,
    set_startup_enabled,
)


@pytest.fixture(scope="session")
def qapp():
    """Ensures QApplication instance exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def temp_config(tmp_path):
    """Provides an isolated ConfigManager backed by temporary ini file."""
    ini_file = str(tmp_path / "test_settings.ini")
    settings = QSettings(ini_file, QSettings.Format.IniFormat)
    settings.clear()
    return ConfigManager(settings=settings)


class DummyController(QObject):
    """QObject mock for DictationController with real signals."""

    state_changed = Signal(AppState)
    hotkey_updated = Signal(str)
    amplitude_updated = Signal(float)
    status_text_updated = Signal(str)
    subtext_updated = Signal(str)
    text_inserted = Signal(str)
    session_error = Signal(str)

    def __init__(self, config_manager=None):
        super().__init__()
        self.current_hotkey = "Ctrl+Space"
        self.state = AppState.IDLE
        self._config_manager = config_manager
        self.cleanup = MagicMock()
        self.toggle_dictation = MagicMock()
        self.cancel_dictation = MagicMock()


@pytest.fixture
def mock_controller(temp_config):
    """Creates a mock DictationController for tray and coordinator tests."""
    return DummyController(config_manager=temp_config)



# =============================================================================
# 1. Startup Registry Tests
# =============================================================================

def test_startup_get_app_command():
    cmd = get_app_command()
    assert sys.executable in cmd


def test_startup_winreg_enabled_and_disabled(monkeypatch):
    registry_store = {}

    class MockKey:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def mock_open_key(hkey, subkey, reserved, access):
        return MockKey()

    def mock_query_value_ex(key, name):
        if name in registry_store:
            return (registry_store[name], 1)
        raise FileNotFoundError()

    def mock_set_value_ex(key, name, reserved, reg_type, val):
        registry_store[name] = val

    def mock_delete_value(key, name):
        if name in registry_store:
            del registry_store[name]
        else:
            raise FileNotFoundError()

    import winreg
    monkeypatch.setattr(winreg, "OpenKey", mock_open_key)
    monkeypatch.setattr(winreg, "QueryValueEx", mock_query_value_ex)
    monkeypatch.setattr(winreg, "SetValueEx", mock_set_value_ex)
    monkeypatch.setattr(winreg, "DeleteValue", mock_delete_value)
    monkeypatch.setattr(sys, "platform", "win32")

    # Initially not enabled
    assert is_startup_enabled("TestApp") is False

    # Enable startup
    res = set_startup_enabled(True, app_name="TestApp", command='"C:\\App.exe"')
    assert res is True
    assert is_startup_enabled("TestApp") is True

    # Disable startup
    res = set_startup_enabled(False, app_name="TestApp")
    assert res is True
    assert is_startup_enabled("TestApp") is False


# =============================================================================
# 2. System Tray Tests
# =============================================================================

def test_system_tray_creation_and_icon(qapp, mock_controller):
    icon = create_default_tray_icon()
    assert not icon.isNull()

    tray = SystemTrayIcon(controller=mock_controller)
    assert tray is not None
    assert tray.toolTip() == "Voice Dictation - Dictado por Voz"


def test_system_tray_menu_actions(qapp, mock_controller):
    tray = SystemTrayIcon(controller=mock_controller)
    menu = tray.contextMenu()
    assert menu is not None

    actions = [a.text() for a in menu.actions()]
    assert any("Voice Dictation" in a for a in actions)
    assert any("Iniciar dictado" in a for a in actions)
    assert any("Configuración..." in a for a in actions)
    assert any("Cambiar atajo..." in a for a in actions)
    assert any("Acerca de..." in a for a in actions)
    assert any("Salir" in a for a in actions)


def test_system_tray_dynamic_hotkey_update(qapp, mock_controller):
    tray = SystemTrayIcon(controller=mock_controller)

    # Emit hotkey updated
    mock_controller.hotkey_updated.emit("Ctrl+Shift+D")
    actions = [a.text() for a in tray.contextMenu().actions()]
    dictation_action = next(a for a in actions if "dictado" in a.lower())
    assert "Ctrl+Shift+D" in dictation_action


def test_system_tray_state_change_update(qapp, mock_controller):
    tray = SystemTrayIcon(controller=mock_controller)

    # Transition to LISTENING
    mock_controller.state = AppState.LISTENING
    mock_controller.state_changed.emit(AppState.LISTENING)

    actions = [a.text() for a in tray.contextMenu().actions()]
    dictation_action = next(a for a in actions if "dictado" in a.lower())
    assert "Detener dictado" in dictation_action
    assert "Escuchando" in tray.toolTip()

    # Transition back to IDLE
    mock_controller.state = AppState.IDLE
    mock_controller.state_changed.emit(AppState.IDLE)
    actions = [a.text() for a in tray.contextMenu().actions()]
    dictation_action = next(a for a in actions if "dictado" in a.lower())
    assert "Iniciar dictado" in dictation_action


def test_system_tray_activation_signals(qapp, mock_controller):
    opened_tabs = []
    quit_called = []

    tray = SystemTrayIcon(
        controller=mock_controller,
        on_open_settings=lambda tab: opened_tabs.append(tab),
        on_quit=lambda: quit_called.append(True),
    )

    tray.open_settings("dictation")
    assert opened_tabs == ["dictation"]

    tray._on_quit_triggered()
    assert quit_called == [True]


# =============================================================================
# 3. FirstRunWizard Tests
# =============================================================================

def test_first_run_wizard_init(qapp, temp_config):
    wizard = FirstRunWizard(config_manager=temp_config)
    assert wizard.windowTitle() == "Bienvenido a Voice Dictation"
    assert wizard._selected_hotkey == "Ctrl+Space"
    assert wizard._badges_row.count() > 0


def test_first_run_wizard_toggle_hotkey_selector(qapp, temp_config):
    wizard = FirstRunWizard(config_manager=temp_config)
    assert wizard._hotkey_selector.isHidden() is True

    wizard._toggle_hotkey_selector()
    assert wizard._hotkey_selector.isHidden() is False

    wizard._toggle_hotkey_selector()
    assert wizard._hotkey_selector.isHidden() is True
    wizard.close()


def test_first_run_wizard_finish_saves_config(qapp, temp_config):
    assert temp_config.is_first_run() is True

    wizard = FirstRunWizard(config_manager=temp_config)
    wizard._auto_paste_check.setChecked(False)
    wizard._on_finish()

    assert temp_config.is_first_run() is False
    assert temp_config.get_auto_paste() is False
    assert temp_config.get_hotkey() == "Ctrl+Space"


# =============================================================================
# 4. SettingsWindow Tests
# =============================================================================

def test_settings_window_init_and_tabs(qapp, temp_config):
    settings = SettingsWindow(config_manager=temp_config)
    assert settings._tabs.count() == 4
    tab_names = [settings._tabs.tabText(i) for i in range(4)]
    assert tab_names == ["General", "Dictado", "Apariencia", "Acerca de"]


def test_settings_window_select_tab(qapp, temp_config):
    settings = SettingsWindow(config_manager=temp_config)
    settings.select_tab("dictation")
    assert settings._tabs.currentIndex() == 1

    settings.select_tab("appearance")
    assert settings._tabs.currentIndex() == 2

    settings.select_tab("about")
    assert settings._tabs.currentIndex() == 3

    settings.select_tab("general")
    assert settings._tabs.currentIndex() == 0


def test_settings_window_general_tab_changes(qapp, temp_config):
    settings = SettingsWindow(config_manager=temp_config)
    signal_fired = []
    settings.settings_updated.connect(lambda: signal_fired.append(True))

    # Toggle auto paste
    settings._auto_paste_check.setChecked(False)
    assert temp_config.get_auto_paste() is False
    assert len(signal_fired) >= 1

    # Change language
    settings._lang_combo.setCurrentIndex(1)  # English
    assert temp_config.get_language() == "en"


def test_settings_window_dictation_tab_changes(qapp, temp_config):
    settings = SettingsWindow(config_manager=temp_config)

    # Change auto-pause slider to 2.2 seconds (value 22)
    settings._slider_pause.setValue(22)
    assert temp_config.get_auto_pause_seconds() == 2.2
    assert "2.2" in settings._lbl_pause_val.text()

    # Change Whisper model to 'small'
    settings._model_combo.setCurrentIndex(1)
    assert temp_config.get_model_name() == "small"


def test_settings_window_appearance_tab_changes(qapp, temp_config):
    settings = SettingsWindow(config_manager=temp_config)

    # Change position to 'bottom'
    settings._pos_combo.setCurrentIndex(1)
    assert temp_config.get_overlay_position() == "bottom"

    # Change size to 'compact'
    settings._size_combo.setCurrentIndex(1)
    assert temp_config.get_overlay_size() == "compact"


# =============================================================================
# 5. MainWindow Lifecycle Coordinator Tests
# =============================================================================

def test_main_window_init(qapp, temp_config, mock_controller):
    main_window = MainWindow(
        config_manager=temp_config,
        controller=mock_controller,
    )
    assert main_window.controller is not None
    assert main_window.overlay is not None
    assert main_window.tray is not None


def test_main_window_start_first_run(qapp, temp_config, mock_controller):
    temp_config._settings.setValue("first_run_completed", False)
    assert temp_config.is_first_run() is True

    main_window = MainWindow(
        config_manager=temp_config,
        controller=mock_controller,
    )

    with patch.object(main_window, "show_first_run") as mock_show_first:
        main_window.start()
        mock_show_first.assert_called_once()


def test_main_window_open_settings(qapp, temp_config, mock_controller):
    main_window = MainWindow(
        config_manager=temp_config,
        controller=mock_controller,
    )

    main_window.open_settings("dictation")
    assert main_window._settings_window is not None
    assert main_window._settings_window.isVisible() is True
    assert main_window._settings_window._tabs.currentIndex() == 1
    main_window.quit()

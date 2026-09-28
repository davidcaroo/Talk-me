import os
import pytest
from pathlib import Path
from PySide6.QtCore import QSettings

from utils.paths import get_app_data_dir, get_models_dir, get_logs_dir, get_assets_dir
from models.app_state import AppState
from models.transcription_result import TranscriptionResult
from utils.config import ConfigManager, DEFAULT_HOTKEY
from utils.logger import setup_logging, get_logger


@pytest.fixture
def temp_settings(tmp_path):
    """Provides an isolated QSettings object backed by a temp ini file."""
    ini_path = str(tmp_path / "test_settings.ini")
    settings = QSettings(ini_path, QSettings.Format.IniFormat)
    settings.clear()
    return settings


def test_paths():
    app_data = get_app_data_dir()
    assert isinstance(app_data, Path)
    assert app_data.exists()
    assert app_data.name == "VoiceDictation"

    models_dir = get_models_dir()
    assert isinstance(models_dir, Path)
    assert models_dir.exists()
    assert models_dir.name == "models"
    assert models_dir.parent == app_data

    logs_dir = get_logs_dir()
    assert isinstance(logs_dir, Path)
    assert logs_dir.exists()
    assert logs_dir.name == "logs"
    assert logs_dir.parent == app_data

    assets_dir = get_assets_dir()
    assert isinstance(assets_dir, Path)
    assert assets_dir.name == "assets"


def test_app_state_enum():
    assert AppState.IDLE.value == "idle"
    assert AppState.LISTENING.value == "listening"
    assert AppState.PAUSED.value == "paused"
    assert AppState.TRANSCRIBING.value == "transcribing"
    assert AppState.PASTING.value == "pasting"
    assert AppState.DONE.value == "done"
    assert AppState.ERROR.value == "error"


def test_transcription_result():
    res = TranscriptionResult(text="Hola mundo", duration=1.2)
    assert res.text == "Hola mundo"
    assert res.duration == 1.2
    assert res.language == "es"
    assert res.success is True
    assert res.error is None

    err_res = TranscriptionResult(
        text="", duration=0.0, language="es", success=False, error="Error de audio"
    )
    assert err_res.success is False
    assert err_res.error == "Error de audio"


def test_config_defaults(temp_settings):
    config = ConfigManager(settings=temp_settings)
    assert DEFAULT_HOTKEY == "Ctrl+Space"
    assert config.get_hotkey() == "Ctrl+Space"
    assert config.get_auto_paste() is True
    assert config.get_auto_pause_seconds() == 1.5
    assert config.get_microphone_index() is None
    assert config.get_language() == "es"
    assert config.get_model_name() == "base"
    assert config.get_overlay_position() == "top"
    assert config.get_overlay_size() == "normal"
    assert config.is_first_run() is True


def test_config_setters_and_persistence(temp_settings):
    config = ConfigManager(settings=temp_settings)

    config.set_hotkey("Ctrl+Shift+D")
    assert config.get_hotkey() == "Ctrl+Shift+D"

    config.restore_default_hotkey()
    assert config.get_hotkey() == "Ctrl+Space"

    config.set_auto_paste(False)
    assert config.get_auto_paste() is False

    config.set_auto_pause_seconds(2.5)
    assert config.get_auto_pause_seconds() == 2.5

    config.set_microphone_index(3)
    assert config.get_microphone_index() == 3

    config.set_microphone_index(None)
    assert config.get_microphone_index() is None

    config.set_language("en")
    assert config.get_language() == "en"

    config.set_model_name("small")
    assert config.get_model_name() == "small"

    config.set_overlay_position("bottom")
    assert config.get_overlay_position() == "bottom"

    config.set_overlay_size("compact")
    assert config.get_overlay_size() == "compact"

    config.set_first_run_completed()
    assert config.is_first_run() is False


def test_logger(tmp_path, monkeypatch):
    log_file = tmp_path / "app.log"
    logger = setup_logging(log_file=log_file)
    assert logger is not None
    logger.info("Test message for logger")

    # Flush handlers to ensure content is written
    for handler in logger.handlers:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test message for logger" in content

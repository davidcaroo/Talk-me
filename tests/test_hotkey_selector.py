import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from utils.config import ConfigManager, DEFAULT_HOTKEY
from input.hotkey_manager import HotkeyManager
from app.widgets.hotkey_selector import HotkeySelector


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_config(tmp_path):
    settings_file = str(tmp_path / "test_selector_settings.ini")
    settings = QSettings(settings_file, QSettings.Format.IniFormat)
    settings.clear()
    return ConfigManager(settings)


@pytest.fixture
def mock_hotkey_manager(temp_config):
    manager = MagicMock(spec=HotkeyManager)
    manager.get_current_hotkey.return_value = temp_config.get_hotkey()
    manager.validate_hotkey = HotkeyManager.validate_hotkey
    manager.normalize_hotkey = HotkeyManager.normalize_hotkey
    manager.is_hotkey_available.return_value = (True, "")
    manager.register_hotkey.return_value = (True, "")
    return manager


class TestHotkeySelectorInit:
    def test_initialization_with_config(self, qapp, temp_config, mock_hotkey_manager):
        temp_config.set_hotkey("Ctrl+Space")
        mock_hotkey_manager.get_current_hotkey.return_value = "Ctrl+Space"

        widget = HotkeySelector(
            hotkey_manager=mock_hotkey_manager,
            config_manager=temp_config
        )
        assert widget.get_current_hotkey() == "Ctrl+Space"
        assert not widget.is_capturing()
        assert widget.save_button.isEnabled() is False  # unchanged, not pending save
        assert "Ctrl" in widget.get_display_text()
        assert "Space" in widget.get_display_text()

    def test_initialization_without_args(self, qapp):
        # Should initialize gracefully with default configs
        with patch.object(HotkeyManager, "__init__", return_value=None):
            widget = HotkeySelector()
            assert widget.get_current_hotkey() == DEFAULT_HOTKEY


class TestHotkeyCaptureMode:
    def test_start_and_cancel_capture(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        cancelled_signals = []
        widget.capture_cancelled.connect(lambda: cancelled_signals.append(True))

        assert not widget.is_capturing()

        # Click or start capture
        widget.capture_button.click()
        assert widget.is_capturing()
        assert "Presiona la nueva combinación" in widget.capture_button.text() or "Presiona" in widget.feedback_label.text()

        # Cancel capture via Esc or cancel_capture
        widget.cancel_capture()
        assert not widget.is_capturing()
        assert len(cancelled_signals) == 1

    def test_escape_key_cancels_capture(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        cancelled_signals = []
        widget.capture_cancelled.connect(lambda: cancelled_signals.append(True))

        widget.start_capture()
        assert widget.is_capturing()

        # Send Escape key event
        esc_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        widget.keyPressEvent(esc_event)

        assert not widget.is_capturing()
        assert len(cancelled_signals) == 1

    def test_capture_key_combination(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        widget.start_capture()

        # Press Ctrl + Shift + D
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_D,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
            "d"
        )
        widget.keyPressEvent(event)

        assert widget.get_candidate_hotkey() == "Ctrl+Shift+D"
        assert not widget.is_capturing()
        assert widget.save_button.isEnabled() is True


class TestHotkeyValidationFeedback:
    def test_invalid_single_key_shows_warning(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        widget.start_capture()

        # Press single key 'A' without modifiers
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, "a")
        widget.keyPressEvent(event)

        assert widget.save_button.isEnabled() is False
        assert "modificadora" in widget.feedback_label.text().lower()

    def test_occupied_hotkey_shows_conflict_error(self, qapp, temp_config, mock_hotkey_manager):
        mock_hotkey_manager.is_hotkey_available.return_value = (
            False,
            "Esta combinación ya está siendo utilizada por otra aplicación o por Windows."
        )

        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        widget.start_capture()

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_F8,
            Qt.KeyboardModifier.ControlModifier,
            ""
        )
        widget.keyPressEvent(event)

        assert widget.save_button.isEnabled() is False
        assert "utilizada por otra aplicación" in widget.feedback_label.text()


class TestHotkeySaveAndRestore:
    def test_save_hotkey_emits_signal(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        saved_signals = []
        widget.hotkey_saved.connect(lambda k: saved_signals.append(k))

        widget.start_capture()
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_F9,
            Qt.KeyboardModifier.ControlModifier,
            ""
        )
        widget.keyPressEvent(event)

        assert widget.save_button.isEnabled() is True
        widget.save_button.click()

        assert saved_signals == ["Ctrl+F9"]
        assert widget.get_current_hotkey() == "Ctrl+F9"
        mock_hotkey_manager.register_hotkey.assert_called_with("Ctrl+F9")

    def test_restore_recommended_hotkey(self, qapp, temp_config, mock_hotkey_manager):
        temp_config.set_hotkey("Ctrl+Shift+D")
        mock_hotkey_manager.get_current_hotkey.return_value = "Ctrl+Shift+D"

        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        assert widget.get_current_hotkey() == "Ctrl+Shift+D"

        # Click restore button
        widget.restore_button.click()

        assert widget.get_candidate_hotkey() == DEFAULT_HOTKEY
        assert widget.save_button.isEnabled() is True
        assert not widget.is_capturing()

    def test_restore_when_already_default(self, qapp, temp_config, mock_hotkey_manager):
        temp_config.set_hotkey(DEFAULT_HOTKEY)
        mock_hotkey_manager.get_current_hotkey.return_value = DEFAULT_HOTKEY

        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        widget.restore_button.click()

        assert widget.get_candidate_hotkey() == DEFAULT_HOTKEY
        assert widget.save_button.isEnabled() is False  # Already configured, no save needed
        assert "actual" in widget.feedback_label.text().lower()

    def test_save_hotkey_registration_failure(self, qapp, temp_config, mock_hotkey_manager):
        mock_hotkey_manager.register_hotkey.return_value = (False, "Fallo al registrar atajo en Windows.")
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)

        widget.start_capture()
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F9, Qt.KeyboardModifier.ControlModifier, "")
        widget.keyPressEvent(event)

        assert widget.save_button.isEnabled() is True
        widget.save_button.click()

        assert widget.save_button.isEnabled() is False
        assert "Fallo al registrar" in widget.feedback_label.text()


class TestHotkeySelectorDetails:
    def test_modifier_only_updates_preview(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        widget.start_capture()

        # Press only Ctrl
        ctrl_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Control, Qt.KeyboardModifier.ControlModifier)
        widget.keyPressEvent(ctrl_event)

        # Still capturing, but badges show Ctrl
        assert widget.is_capturing()
        assert widget._badges_layout.count() >= 1

    def test_function_key_without_modifiers_accepted(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        widget.start_capture()

        # Press F6
        f6_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F6, Qt.KeyboardModifier.NoModifier)
        widget.keyPressEvent(f6_event)

        assert not widget.is_capturing()
        assert widget.get_candidate_hotkey() == "F6"
        assert widget.save_button.isEnabled() is True
        assert "válida" in widget.feedback_label.text().lower()

    def test_click_capture_button_again_toggles_cancel(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        widget.capture_button.click()
        assert widget.is_capturing()

        # Click again to cancel
        widget.capture_button.click()
        assert not widget.is_capturing()

    def test_badges_rendered_properly(self, qapp, temp_config, mock_hotkey_manager):
        widget = HotkeySelector(hotkey_manager=mock_hotkey_manager, config_manager=temp_config)
        widget._update_badges("Ctrl+Shift+D")

        # 3 badges (Ctrl, Shift, D) + 2 separators (+) = 5 widgets
        assert widget._badges_layout.count() == 5


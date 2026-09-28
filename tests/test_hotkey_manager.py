import pytest
import time
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QSettings

from utils.config import ConfigManager, DEFAULT_HOTKEY
from input.hotkey_manager import HotkeyManager


@pytest.fixture
def temp_config(tmp_path):
    settings_file = str(tmp_path / "test_hotkey_settings.ini")
    settings = QSettings(settings_file, QSettings.Format.IniFormat)
    settings.clear()
    return ConfigManager(settings)


class TestHotkeyNormalization:
    def test_normalize_spaces_and_casing(self):
        assert HotkeyManager.normalize_hotkey("ctrl + space") == "Ctrl+Space"
        assert HotkeyManager.normalize_hotkey("control+shift+d") == "Ctrl+Shift+D"
        assert HotkeyManager.normalize_hotkey("CONTROL + ALT + SPACE") == "Ctrl+Alt+Space"
        assert HotkeyManager.normalize_hotkey("shift+ctrl+space") == "Ctrl+Shift+Space"
        assert HotkeyManager.normalize_hotkey("win + alt + space") == "Alt+Win+Space"
        assert HotkeyManager.normalize_hotkey("f7") == "F7"
        assert HotkeyManager.normalize_hotkey("ctrl + f8") == "Ctrl+F8"

    def test_normalize_special_keys(self):
        assert HotkeyManager.normalize_hotkey("ctrl+spacebar") == "Ctrl+Space"
        assert HotkeyManager.normalize_hotkey("ctrl+alt+del") == "Ctrl+Alt+Delete"
        assert HotkeyManager.normalize_hotkey("ctrl+esc") == "Ctrl+Esc"
        assert HotkeyManager.normalize_hotkey("alt+return") == "Alt+Enter"

    def test_normalize_empty(self):
        assert HotkeyManager.normalize_hotkey("") == ""
        assert HotkeyManager.normalize_hotkey("   ") == ""


class TestHotkeyValidation:
    def test_empty_or_whitespace_rejected(self):
        valid, reason = HotkeyManager.validate_hotkey("")
        assert not valid
        assert "vacío" in reason.lower()

        valid, reason = HotkeyManager.validate_hotkey("   ")
        assert not valid
        assert "vacío" in reason.lower()

    def test_single_alphanumeric_rejected(self):
        for key in ["A", "a", "1", "z", "9"]:
            valid, reason = HotkeyManager.validate_hotkey(key)
            assert not valid
            assert "alfanumérica" in reason.lower() or "modificadora" in reason.lower()

    def test_single_non_function_rejected(self):
        for key in ["Space", "Enter", "Tab", "Esc"]:
            valid, reason = HotkeyManager.validate_hotkey(key)
            assert not valid
            assert "modificadora" in reason.lower() or "función" in reason.lower()

    def test_function_keys_f1_to_f12_accepted_without_modifiers(self):
        for i in range(1, 13):
            valid, reason = HotkeyManager.validate_hotkey(f"F{i}")
            assert valid, f"F{i} should be valid without modifiers, got: {reason}"
            assert reason == ""

    def test_prohibited_system_combinations_rejected(self):
        prohibited = [
            "Ctrl+Alt+Delete",
            "Ctrl+Alt+Del",
            "Win+L",
            "Alt+Tab",
            "Alt+F4",
            "ctrl+alt+del",
            "win+l",
            "alt+f4",
        ]
        for combo in prohibited:
            valid, reason = HotkeyManager.validate_hotkey(combo)
            assert not valid, f"{combo} should be rejected"
            assert "reservado" in reason.lower() or "sistema" in reason.lower()

    def test_valid_combinations_accepted(self):
        valid_combos = [
            "Ctrl+Space",
            "Ctrl+Shift+D",
            "Alt+Shift+F8",
            "Win+Space",
            "Ctrl+Alt+K",
        ]
        for combo in valid_combos:
            valid, reason = HotkeyManager.validate_hotkey(combo)
            assert valid, f"{combo} should be valid, got: {reason}"
            assert reason == ""

    def test_only_modifiers_rejected(self):
        for combo in ["Ctrl", "Ctrl+Shift", "Alt", "Win+Alt"]:
            valid, reason = HotkeyManager.validate_hotkey(combo)
            assert not valid
            assert "principal" in reason.lower()

    def test_unrecognized_key_rejected(self):
        valid, reason = HotkeyManager.validate_hotkey("Ctrl+NonExistentKey999")
        assert not valid
        assert "no reconocida" in reason.lower()

    def test_multiple_base_keys_rejected(self):
        valid, reason = HotkeyManager.validate_hotkey("Ctrl+A+B")
        assert not valid
        assert "múltiples" in reason.lower()


class TestHotkeyManagerRegistration:
    def test_register_and_unregister_lifecycle(self, temp_config):
        mgr = HotkeyManager(config_manager=temp_config)
        registered_signals = []
        mgr.hotkey_registered.connect(lambda k: registered_signals.append(k))

        try:
            # Register a safe test hotkey
            test_hotkey = "Ctrl+Shift+F8"
            success, msg = mgr.register_hotkey(test_hotkey)
            assert success, f"Failed to register {test_hotkey}: {msg}"
            assert mgr.is_registered()
            assert mgr.get_current_hotkey() == test_hotkey
            assert registered_signals == [test_hotkey]
            assert temp_config.get_hotkey() == test_hotkey

            # Unregister
            mgr.unregister_hotkey()
            assert not mgr.is_registered()
            assert mgr.get_current_hotkey() == ""
        finally:
            mgr.cleanup()

    def test_update_hotkey_high_level(self, temp_config):
        mgr = HotkeyManager(config_manager=temp_config)
        try:
            test_hotkey = "Ctrl+Shift+F7"
            success, msg = mgr.update_hotkey(test_hotkey)
            assert success, f"Failed to update hotkey: {msg}"
            assert mgr.is_registered()
            assert mgr.get_current_hotkey() == test_hotkey
            assert temp_config.get_hotkey() == test_hotkey
        finally:
            mgr.cleanup()

    def test_register_invalid_hotkey_fails(self, temp_config):
        mgr = HotkeyManager(config_manager=temp_config)
        failed_signals = []
        mgr.registration_failed.connect(lambda err: failed_signals.append(err))

        try:
            success, msg = mgr.register_hotkey("A")
            assert not success
            assert not mgr.is_registered()
            assert len(failed_signals) == 1
            assert failed_signals[0] == msg
        finally:
            mgr.cleanup()

    def test_conflict_detection_real_win32(self, temp_config):
        mgr1 = HotkeyManager(config_manager=temp_config)
        mgr2 = HotkeyManager(config_manager=temp_config)
        test_hotkey = "Ctrl+Shift+F8"

        try:
            # Register with mgr1
            ok1, msg1 = mgr1.register_hotkey(test_hotkey)
            assert ok1, f"mgr1 failed to register: {msg1}"

            # Try to register same with mgr2
            ok2, msg2 = mgr2.register_hotkey(test_hotkey)
            assert not ok2, "mgr2 should have failed due to conflict"
            assert "utilizada" in msg2.lower() or "conflicto" in msg2.lower()
            assert not mgr2.is_registered()
        finally:
            mgr1.cleanup()
            mgr2.cleanup()

    def test_conflict_detection_mocked_error_1409(self, temp_config):
        mgr = HotkeyManager(config_manager=temp_config)
        failed_signals = []
        mgr.registration_failed.connect(lambda err: failed_signals.append(err))

        try:
            with patch("ctypes.windll.user32.RegisterHotKey", return_value=0), \
                 patch("ctypes.windll.kernel32.GetLastError", return_value=1409):
                success, msg = mgr.register_hotkey("Ctrl+Space")
                assert not success
                assert "utilizada por otra aplicación o por Windows" in msg
                assert len(failed_signals) == 1
                assert "utilizada por otra aplicación o por Windows" in failed_signals[0]
                assert not mgr.is_registered()
        finally:
            mgr.cleanup()

    def test_hotkey_triggered_signal(self, temp_config):
        mgr = HotkeyManager(config_manager=temp_config)
        triggered = []
        mgr.hotkey_triggered.connect(lambda: triggered.append(True))

        try:
            ok, msg = mgr.register_hotkey("Ctrl+Shift+F8")
            assert ok

            # Simulate hotkey message or trigger directly
            mgr._trigger_hotkey()
            assert len(triggered) == 1
        finally:
            mgr.cleanup()

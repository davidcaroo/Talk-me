"""Unit tests for clipboard and paste automation (Task 6)."""

import sys
from unittest.mock import MagicMock, call, patch
import pytest

from input.clipboard import Clipboard
from input.paste import Paster, VK_CONTROL, VK_V, KEYEVENTF_KEYUP


class TestClipboard:
    """Tests for Clipboard class: copy, get_text, clear with Unicode and multiline support."""

    UNICODE_SAMPLE = "¡Hola mundo! Español: pingüino, cañón, árbol, 100% éxito."
    MULTILINE_SAMPLE = (
        "Línea 1: Inicio de transcripción\n"
        "Línea 2: Contiene tildes (á, é, í, ó, ú) y eñes (ñ, Ñ)\n"
        "Línea 3: Símbolos matemáticos y especiales: ¿Cómo estás? ¡Genial! 100% € $\n"
        "Línea 4: Fin de prueba."
    )

    def test_copy_unicode_text_pyperclip_fallback(self):
        """Test copying complex Unicode strings via pyperclip fallback."""
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=None):
            with patch("pyperclip.copy") as mock_copy:
                success = Clipboard.copy(self.UNICODE_SAMPLE)
                assert success is True
                mock_copy.assert_called_once_with(self.UNICODE_SAMPLE)

    def test_copy_multiline_text_pyperclip_fallback(self):
        """Test copying multiline text via pyperclip fallback."""
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=None):
            with patch("pyperclip.copy") as mock_copy:
                success = Clipboard.copy(self.MULTILINE_SAMPLE)
                assert success is True
                mock_copy.assert_called_once_with(self.MULTILINE_SAMPLE)

    def test_copy_using_qt_clipboard(self):
        """Test copying when Qt application clipboard is active."""
        mock_qt_cb = MagicMock()
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=mock_qt_cb):
            with patch("pyperclip.copy") as mock_pyperclip:
                success = Clipboard.copy(self.UNICODE_SAMPLE)
                assert success is True
                mock_qt_cb.setText.assert_called_once_with(self.UNICODE_SAMPLE)
                mock_pyperclip.assert_not_called()

    def test_copy_qt_fallback_to_pyperclip_on_error(self):
        """Test that if Qt clipboard throws an error, it falls back to pyperclip."""
        mock_qt_cb = MagicMock()
        mock_qt_cb.setText.side_effect = RuntimeError("Qt clipboard busy")
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=mock_qt_cb):
            with patch("pyperclip.copy") as mock_pyperclip:
                success = Clipboard.copy(self.UNICODE_SAMPLE)
                assert success is True
                mock_pyperclip.assert_called_once_with(self.UNICODE_SAMPLE)

    def test_copy_failure_returns_false(self):
        """Test that if both Qt and pyperclip fail, copy returns False without crashing."""
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=None):
            with patch("pyperclip.copy", side_effect=Exception("Pyperclip failure")):
                success = Clipboard.copy("test")
                assert success is False

    def test_copy_coerces_non_string(self):
        """Test that non-string values are converted to string."""
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=None):
            with patch("pyperclip.copy") as mock_copy:
                success = Clipboard.copy(12345)  # type: ignore
                assert success is True
                mock_copy.assert_called_once_with("12345")

    def test_get_text_qt(self):
        """Test get_text using Qt clipboard."""
        mock_qt_cb = MagicMock()
        mock_qt_cb.text.return_value = self.UNICODE_SAMPLE
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=mock_qt_cb):
            text = Clipboard.get_text()
            assert text == self.UNICODE_SAMPLE

    def test_get_text_pyperclip(self):
        """Test get_text fallback to pyperclip."""
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=None):
            with patch("pyperclip.paste", return_value=self.UNICODE_SAMPLE) as mock_paste:
                text = Clipboard.get_text()
                assert text == self.UNICODE_SAMPLE
                mock_paste.assert_called_once()

    def test_get_text_error_returns_empty_string(self):
        """Test get_text returns empty string on exception."""
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=None):
            with patch("pyperclip.paste", side_effect=Exception("Read error")):
                text = Clipboard.get_text()
                assert text == ""

    def test_clear_qt(self):
        """Test clear clipboard with Qt clipboard."""
        mock_qt_cb = MagicMock()
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=mock_qt_cb):
            with patch("pyperclip.copy") as mock_pyperclip:
                Clipboard.clear()
                mock_qt_cb.clear.assert_called_once()
                mock_pyperclip.assert_not_called()

    def test_clear_pyperclip(self):
        """Test clear clipboard fallback with pyperclip."""
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=None):
            with patch("pyperclip.copy") as mock_copy:
                Clipboard.clear()
                mock_copy.assert_called_once_with("")

    def test_clear_error_does_not_crash(self):
        """Test clear clipboard handles errors gracefully."""
        with patch.object(Clipboard, "_get_qt_clipboard", return_value=None):
            with patch("pyperclip.copy", side_effect=Exception("Clear error")):
                # Should not raise exception
                Clipboard.clear()

    def test_clipboard_instance_methods(self):
        """Verify Clipboard works both as class/static methods and as instance."""
        inst = Clipboard()
        with patch.object(Clipboard, "copy", return_value=True) as mock_copy:
            assert inst.copy("hello") is True
            mock_copy.assert_called_once_with("hello")


class TestPaster:
    """Tests for Paster class: Win32 SendInput and pynput fallback."""

    def test_paste_clipboard_sendinput_success(self):
        """Test paste_clipboard using Win32 SendInput."""
        with patch("sys.platform", "win32"):
            with patch("time.sleep") as mock_sleep:
                # Mock _send_input_paste
                with patch("input.paste._send_input_paste", return_value=True) as mock_sendinput:
                    with patch("input.paste._pynput_paste") as mock_pynput:
                        success = Paster.paste_clipboard(delay_ms=50)
                        assert success is True
                        mock_sleep.assert_called_once_with(0.05)
                        mock_sendinput.assert_called_once()
                        mock_pynput.assert_not_called()

    def test_paste_clipboard_sendinput_structure_and_keys(self):
        """Test that SendInput receives the exact 4 keyboard input events with correct virtual key codes."""
        if sys.platform != "win32":
            pytest.skip("Test requires win32 platform for ctypes structures")

        import ctypes
        from input.paste import _send_input_paste, INPUT

        mock_user32 = MagicMock()
        captured_inputs = []

        def fake_send_input(nInputs, pInputs, cbSize):
            # pInputs is an array of INPUT
            assert nInputs == 4
            assert cbSize == ctypes.sizeof(INPUT)
            # Capture inputs
            for i in range(nInputs):
                captured_inputs.append((pInputs[i].union.ki.wVk, pInputs[i].union.ki.dwFlags))
            return 4

        mock_user32.SendInput = fake_send_input

        with patch("ctypes.windll.user32", mock_user32):
            result = _send_input_paste()
            assert result is True
            assert len(captured_inputs) == 4
            # 1. Ctrl Down
            assert captured_inputs[0] == (VK_CONTROL, 0)
            # 2. V Down
            assert captured_inputs[1] == (VK_V, 0)
            # 3. V Up
            assert captured_inputs[2] == (VK_V, KEYEVENTF_KEYUP)
            # 4. Ctrl Up
            assert captured_inputs[3] == (VK_CONTROL, KEYEVENTF_KEYUP)

    def test_paste_clipboard_fallback_to_pynput_when_sendinput_fails(self):
        """Test fallback to pynput when SendInput returns False."""
        with patch("time.sleep"):
            with patch("input.paste._send_input_paste", return_value=False):
                with patch("input.paste._pynput_paste", return_value=True) as mock_pynput:
                    success = Paster.paste_clipboard(delay_ms=40)
                    assert success is True
                    mock_pynput.assert_called_once()

    def test_paste_clipboard_fallback_to_pynput_when_sendinput_raises(self):
        """Test fallback to pynput when SendInput raises an exception."""
        with patch("time.sleep"):
            with patch("input.paste._send_input_paste", side_effect=OSError("Win32 error")):
                with patch("input.paste._pynput_paste", return_value=True) as mock_pynput:
                    success = Paster.paste_clipboard(delay_ms=40)
                    assert success is True
                    mock_pynput.assert_called_once()

    def test_paste_clipboard_non_windows_platform(self):
        """Test paste_clipboard on non-windows platform directly uses pynput."""
        with patch("sys.platform", "darwin"):
            with patch("time.sleep"):
                with patch("input.paste._send_input_paste") as mock_sendinput:
                    with patch("input.paste._pynput_paste", return_value=True) as mock_pynput:
                        success = Paster.paste_clipboard(delay_ms=10)
                        assert success is True
                        mock_sendinput.assert_not_called()
                        mock_pynput.assert_called_once()

    def test_paste_clipboard_both_fail(self):
        """Test paste_clipboard returns False when both SendInput and pynput fail."""
        with patch("time.sleep"):
            with patch("input.paste._send_input_paste", return_value=False):
                with patch("input.paste._pynput_paste", return_value=False):
                    success = Paster.paste_clipboard(delay_ms=0)
                    assert success is False

    def test_pynput_paste_mechanism(self):
        """Test _pynput_paste presses and releases Ctrl and V in correct order."""
        from input.paste import _pynput_paste
        from pynput.keyboard import Key

        mock_controller = MagicMock()
        mock_controller_cls = MagicMock(return_value=mock_controller)

        with patch("pynput.keyboard.Controller", mock_controller_cls):
            res = _pynput_paste()
            assert res is True
            # Verify Key.ctrl was pressed first, then 'v' pressed and released, then Key.ctrl released
            mock_controller.press.assert_has_calls([call(Key.ctrl), call('v')])
            mock_controller.release.assert_has_calls([call('v'), call(Key.ctrl)])

    def test_paster_instance_method(self):
        """Verify Paster works as instance as well as class/static method."""
        paster = Paster()
        with patch.object(Paster, "paste_clipboard", return_value=True) as mock_paste:
            assert paster.paste_clipboard(delay_ms=40) is True
            mock_paste.assert_called_once_with(delay_ms=40)

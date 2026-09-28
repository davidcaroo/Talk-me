from unittest.mock import MagicMock, patch
import sys
import pytest

from input.paste import Paster, _send_input_paste, _release_modifier_keys


def test_paster_releases_modifiers_before_paste():
    with patch("input.paste._release_modifier_keys") as mock_release, \
         patch("input.paste._send_input_paste", return_value=True) as mock_send:
        
        success = Paster.paste_clipboard(delay_ms=0)
        assert success is True
        mock_release.assert_called_once()
        mock_send.assert_called_once()


def test_release_modifier_keys_sends_keyup_events():
    if sys.platform != "win32":
        pytest.skip("Windows only test")

    with patch("ctypes.windll.user32.SendInput") as mock_send_input:
        mock_send_input.return_value = 4
        _release_modifier_keys()
        assert mock_send_input.called
        call_args = mock_send_input.call_args[0]
        count = call_args[0]
        assert count == 4


def test_paster_default_delay_is_80ms():
    import inspect
    sig = inspect.signature(Paster.paste_clipboard)
    assert sig.parameters["delay_ms"].default == 80

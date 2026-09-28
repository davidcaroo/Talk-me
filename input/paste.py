"""Keystroke automation for pasting clipboard text into active applications.

Uses Win32 SendInput as the primary mechanism with a safe fallback to pynput,
ensuring keystrokes are sent to the active foreground window without stealing focus.
"""

import logging
import sys
import time
import ctypes

logger = logging.getLogger(__name__)

# Virtual-Key Codes and Constants
VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

# Ctypes structures for Win32 SendInput
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", _INPUT_UNION),
    ]


def _send_input_paste() -> bool:
    """Simulates Ctrl + V keystroke using Win32 SendInput."""
    if sys.platform != "win32":
        return False

    try:
        inputs = (INPUT * 4)(
            # 1. Ctrl key down
            INPUT(
                type=INPUT_KEYBOARD,
                union=_INPUT_UNION(ki=KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)),
            ),
            # 2. V key down
            INPUT(
                type=INPUT_KEYBOARD,
                union=_INPUT_UNION(ki=KEYBDINPUT(wVk=VK_V, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)),
            ),
            # 3. V key up
            INPUT(
                type=INPUT_KEYBOARD,
                union=_INPUT_UNION(ki=KEYBDINPUT(wVk=VK_V, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
            ),
            # 4. Ctrl key up
            INPUT(
                type=INPUT_KEYBOARD,
                union=_INPUT_UNION(ki=KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)),
            ),
        )

        user32 = ctypes.windll.user32
        sent = user32.SendInput(len(inputs), inputs, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            logger.warning(f"SendInput sent {sent} of {len(inputs)} inputs")
            return False
        return True
    except Exception as e:
        logger.warning(f"SendInput failed: {e}", exc_info=True)
        return False


def _pynput_paste() -> bool:
    """Fallback paste implementation using pynput.keyboard.Controller."""
    try:
        from pynput.keyboard import Controller, Key

        controller = Controller()
        controller.press(Key.ctrl)
        try:
            controller.press("v")
            controller.release("v")
        finally:
            controller.release(Key.ctrl)
        return True
    except Exception as e:
        logger.error(f"Pynput paste fallback failed: {e}", exc_info=True)
        return False


class Paster:
    """Automates pasting from clipboard into the currently active application window."""

    @staticmethod
    def paste_clipboard(delay_ms: int = 40) -> bool:
        """Simulates Ctrl + V in the active window.

        Args:
            delay_ms: Stabilization pause in milliseconds before sending the keystrokes
                      to allow the target application window to maintain/stabilize focus.
                      Defaults to 40 ms.

        Returns:
            True if paste event was successfully triggered, False otherwise.
        """
        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)

        # Primary implementation: Win32 SendInput
        if sys.platform == "win32":
            try:
                if _send_input_paste():
                    return True
                logger.info("SendInput failed or incomplete; falling back to pynput.")
            except Exception as e:
                logger.warning(f"SendInput exception: {e}; falling back to pynput.")

        # Fallback: pynput keyboard controller
        return _pynput_paste()

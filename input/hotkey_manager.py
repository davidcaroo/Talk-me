import ctypes
import queue
import re
import sys
import threading
from ctypes import wintypes
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal

from utils.config import ConfigManager, DEFAULT_HOTKEY
from utils.logger import get_logger

logger = get_logger("VoiceDictation.HotkeyManager")

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
ERROR_HOTKEY_ALREADY_REGISTERED = 1409

MODIFIER_CANONICAL = {
    "ctrl": "Ctrl",
    "control": "Ctrl",
    "ctl": "Ctrl",
    "alt": "Alt",
    "alternate": "Alt",
    "option": "Alt",
    "shift": "Shift",
    "win": "Win",
    "windows": "Win",
    "super": "Win",
    "cmd": "Win",
    "command": "Win",
    "meta": "Win",
}

MODIFIER_ORDER = ["Ctrl", "Alt", "Shift", "Win"]

SPECIAL_KEYS_CANONICAL = {
    "space": "Space",
    "spacebar": "Space",
    "esc": "Esc",
    "escape": "Esc",
    "enter": "Enter",
    "return": "Enter",
    "tab": "Tab",
    "backspace": "Backspace",
    "bksp": "Backspace",
    "delete": "Delete",
    "del": "Delete",
    "insert": "Insert",
    "ins": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "page_up": "PageUp",
    "pgup": "PageUp",
    "pagedown": "PageDown",
    "page_down": "PageDown",
    "pgdn": "PageDown",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "capslock": "CapsLock",
    "caps_lock": "CapsLock",
    "caps": "CapsLock",
    "numlock": "NumLock",
    "num_lock": "NumLock",
    "scrolllock": "ScrollLock",
    "scroll_lock": "ScrollLock",
    "printscreen": "PrintScreen",
    "prtscn": "PrintScreen",
    "prntscrn": "PrintScreen",
    "pause": "Pause",
}

PROHIBITED_HOTKEYS = {
    "Ctrl+Alt+Delete",
    "Ctrl+Alt+Del",
    "Win+L",
    "Alt+Tab",
    "Alt+F4",
}

VK_MAP = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "CLEAR": 0x0C,
    "ENTER": 0x0D,
    "PAUSE": 0x13,
    "CAPSLOCK": 0x14,
    "ESC": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "PRINTSCREEN": 0x2C,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
}

# F1 - F24
for _i in range(1, 25):
    VK_MAP[f"F{_i}"] = 0x70 + (_i - 1)

# 0-9
for _i in range(10):
    VK_MAP[str(_i)] = 0x30 + _i

# A-Z
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    VK_MAP[_c] = ord(_c)


def _get_vk_code(key_str: str) -> Optional[int]:
    """Resolves a key name into a Windows Virtual Key code."""
    upper = key_str.upper()
    if upper in VK_MAP:
        return VK_MAP[upper]

    if sys.platform == "win32" and len(key_str) == 1:
        try:
            vk_scan = ctypes.windll.user32.VkKeyScanW(ord(key_str))
            if vk_scan != -1:
                return vk_scan & 0xFF
        except Exception:
            pass

    return None


def _get_modifier_flags(mods: list[str]) -> int:
    """Builds Win32 modifier flags with MOD_NOREPEAT."""
    flags = MOD_NOREPEAT
    for m in mods:
        if m == "Alt":
            flags |= MOD_ALT
        elif m == "Ctrl":
            flags |= MOD_CONTROL
        elif m == "Shift":
            flags |= MOD_SHIFT
        elif m == "Win":
            flags |= MOD_WIN
    return flags


class Win32HotkeyThread(threading.Thread):
    """
    Dedicated worker thread running a Windows message loop for RegisterHotKey / UnregisterHotKey.
    Ensures hotkeys are properly registered and processed without blocking the Qt UI thread.
    """

    def __init__(self, on_hotkey_callback: Callable[[], None]):
        super().__init__(name="Win32HotkeyThread", daemon=True)
        self.on_hotkey_callback = on_hotkey_callback
        self._cmd_queue: queue.Queue = queue.Queue()
        self._ready_event = threading.Event()
        self._running = False
        self._event_handle = None

    def start(self) -> None:
        super().start()
        self._ready_event.wait(timeout=2.0)

    def run(self) -> None:
        if sys.platform != "win32":
            self._running = True
            self._ready_event.set()
            return

        try:
            # Create auto-reset Win32 event for signaling commands
            self._event_handle = ctypes.windll.kernel32.CreateEventW(None, False, False, None)

            # Force creation of thread message queue
            msg = wintypes.MSG()
            ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 0)

            self._running = True
            self._ready_event.set()

            while self._running:
                # Wait for command event or Windows messages (QS_ALLINPUT = 0x04FF)
                ctypes.windll.user32.MsgWaitForMultipleObjects(
                    1,
                    ctypes.byref(wintypes.HANDLE(self._event_handle)),
                    False,
                    100,
                    0x04FF,
                )

                # Process pending commands
                while not self._cmd_queue.empty():
                    try:
                        cmd_type, args, resp_q = self._cmd_queue.get_nowait()
                    except queue.Empty:
                        break

                    if cmd_type == "REGISTER":
                        hotkey_id, fs_mod, vk = args
                        try:
                            ret = ctypes.windll.user32.RegisterHotKey(0, hotkey_id, fs_mod, vk)
                            success = bool(ret)
                            err = ctypes.windll.kernel32.GetLastError() if not success else 0
                        except Exception as e:
                            logger.error(f"Error calling RegisterHotKey: {e}")
                            success = False
                            err = -1
                        if resp_q:
                            resp_q.put((success, err))

                    elif cmd_type == "UNREGISTER":
                        hotkey_id = args
                        try:
                            ret = ctypes.windll.user32.UnregisterHotKey(0, hotkey_id)
                            success = bool(ret)
                        except Exception as e:
                            logger.error(f"Error calling UnregisterHotKey: {e}")
                            success = False
                        if resp_q:
                            resp_q.put(success)

                    elif cmd_type == "STOP":
                        self._running = False
                        if resp_q:
                            resp_q.put(True)
                        break

                if not self._running:
                    break

                # Process Windows message queue
                msg = wintypes.MSG()
                while ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):  # PM_REMOVE = 1
                    if msg.message == WM_HOTKEY:
                        if self.on_hotkey_callback:
                            try:
                                self.on_hotkey_callback()
                            except Exception as ex:
                                logger.error(f"Error executing on_hotkey_callback: {ex}")
                    elif msg.message == WM_QUIT:
                        self._running = False
                        break
                    ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                    ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

        finally:
            self._running = False
            if self._event_handle:
                try:
                    ctypes.windll.kernel32.CloseHandle(self._event_handle)
                except Exception:
                    pass
                self._event_handle = None

    def register_hotkey(
        self, hotkey_id: int, fs_modifiers: int, vk: int, timeout: float = 2.0
    ) -> tuple[bool, int]:
        """Requests the worker thread to call RegisterHotKey."""
        if not self._running:
            return False, -1
        resp_q: queue.Queue = queue.Queue()
        self._cmd_queue.put(("REGISTER", (hotkey_id, fs_modifiers, vk), resp_q))
        if self._event_handle:
            try:
                ctypes.windll.kernel32.SetEvent(self._event_handle)
            except Exception:
                pass
        try:
            return resp_q.get(timeout=timeout)
        except queue.Empty:
            logger.warning("Timeout waiting for RegisterHotKey response")
            return False, -1

    def unregister_hotkey(self, hotkey_id: int, timeout: float = 2.0) -> bool:
        """Requests the worker thread to call UnregisterHotKey."""
        if not self._running:
            return False
        resp_q: queue.Queue = queue.Queue()
        self._cmd_queue.put(("UNREGISTER", hotkey_id, resp_q))
        if self._event_handle:
            try:
                ctypes.windll.kernel32.SetEvent(self._event_handle)
            except Exception:
                pass
        try:
            return resp_q.get(timeout=timeout)
        except queue.Empty:
            logger.warning("Timeout waiting for UnregisterHotKey response")
            return False

    def stop(self, timeout: float = 2.0) -> None:
        """Stops the worker thread and releases resources."""
        if not self.is_alive():
            return
        resp_q: queue.Queue = queue.Queue()
        self._cmd_queue.put(("STOP", None, resp_q))
        if self._event_handle:
            try:
                ctypes.windll.kernel32.SetEvent(self._event_handle)
            except Exception:
                pass
        self.join(timeout=timeout)


class HotkeyManager(QObject):
    """
    Centralized manager for global hotkeys using native Windows RegisterHotKey API.
    Provides conflict detection, key normalization, validation, and Qt signals.
    """

    hotkey_triggered = Signal()
    hotkey_registered = Signal(str)  # Emits current normalized hotkey
    registration_failed = Signal(str)  # Emits error description

    _id_lock = threading.Lock()
    _id_counter = 1

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._config_manager = config_manager or ConfigManager()
        self._current_hotkey: str = ""
        self._is_registered: bool = False

        with HotkeyManager._id_lock:
            self._hotkey_id = HotkeyManager._id_counter
            HotkeyManager._id_counter += 1

        self._thread = Win32HotkeyThread(on_hotkey_callback=self._handle_hotkey_triggered)
        self._thread.start()

    def _handle_hotkey_triggered(self) -> None:
        """Internal callback invoked from Win32 worker thread on WM_HOTKEY."""
        logger.debug(f"Hotkey triggered: {self._current_hotkey}")
        self.hotkey_triggered.emit()

    def _trigger_hotkey(self) -> None:
        """Helper to programmatically trigger the hotkey signal (useful for testing)."""
        self._handle_hotkey_triggered()

    @staticmethod
    def normalize_hotkey(hotkey_str: str) -> str:
        """
        Normalizes a hotkey string (e.g., 'ctrl + space' -> 'Ctrl+Space',
        'control+shift+d' -> 'Ctrl+Shift+D').
        Preserves canonical modifier order: Ctrl, Alt, Shift, Win.
        """
        if not hotkey_str or not hotkey_str.strip():
            return ""

        raw = hotkey_str.strip()
        tokens = [t.strip() for t in raw.split("+") if t.strip()]
        if not tokens:
            return "+" if "+" in raw else ""

        modifiers = set()
        base_keys = []

        for token in tokens:
            lower = token.lower()
            if lower in MODIFIER_CANONICAL:
                modifiers.add(MODIFIER_CANONICAL[lower])
            else:
                if lower in SPECIAL_KEYS_CANONICAL:
                    base_keys.append(SPECIAL_KEYS_CANONICAL[lower])
                elif re.match(r"^f([1-9]|1[0-9]|2[0-4])$", lower):
                    base_keys.append(lower.upper())
                elif len(token) == 1:
                    base_keys.append(token.upper())
                else:
                    base_keys.append(token.capitalize())

        ordered_mods = [m for m in MODIFIER_ORDER if m in modifiers]
        components = ordered_mods + base_keys
        return "+".join(components)

    @staticmethod
    def validate_hotkey(hotkey_str: str) -> tuple[bool, str]:
        """
        Validates hotkey string:
        - Must not be empty
        - Must not use prohibited system shortcuts
        - Must include at least one modifier or be a function key (F1-F12)
        - Must not be a single alphanumeric key without modifiers
        - Must resolve to a valid virtual key
        """
        if not hotkey_str or not hotkey_str.strip():
            return False, "El atajo de teclado no puede estar vacío."

        normalized = HotkeyManager.normalize_hotkey(hotkey_str)

        # Prohibited check
        norm_del_variant = normalized.replace("Delete", "Del")
        if normalized in PROHIBITED_HOTKEYS or norm_del_variant in PROHIBITED_HOTKEYS:
            return False, f"La combinación '{normalized}' es un atajo reservado del sistema."

        parts = normalized.split("+")
        mods = [p for p in parts if p in MODIFIER_ORDER]
        base_keys = [p for p in parts if p not in MODIFIER_ORDER]

        if not base_keys:
            return False, "El atajo debe incluir una tecla principal además de los modificadores."

        if len(base_keys) > 1:
            return False, f"No se pueden combinar múltiples teclas principales ({', '.join(base_keys)})."

        base_key = base_keys[0]
        is_fkey = re.match(r"^F([1-9]|1[0-2])$", base_key) is not None

        if not mods and not is_fkey:
            if len(base_key) == 1 and base_key.isalnum():
                return False, f"No se permite una sola tecla alfanumérica ('{base_key}') sin modificadores."
            return (
                False,
                "El atajo debe incluir al menos una tecla modificadora (Ctrl, Alt, Shift, Win) o ser una tecla de función (F1-F12).",
            )

        vk = _get_vk_code(base_key)
        if vk is None:
            return False, f"Tecla no reconocida: '{base_key}'."

        return True, ""

    def register_hotkey(self, hotkey_str: Optional[str] = None) -> tuple[bool, str]:
        """
        Validates, unregisters previous hotkey if any, and registers hotkey system-wide.
        If registration fails (conflict code 1409 or return 0), reports clear error.
        If successful, updates ConfigManager and emits hotkey_registered.
        """
        if hotkey_str is None:
            hotkey_str = self._config_manager.get_hotkey()

        is_valid, validation_msg = self.validate_hotkey(hotkey_str)
        if not is_valid:
            logger.warning(f"Hotkey validation failed: {validation_msg}")
            self.registration_failed.emit(validation_msg)
            return False, validation_msg

        normalized = self.normalize_hotkey(hotkey_str)

        # Parse modifiers and base key
        parts = normalized.split("+")
        mods = [p for p in parts if p in MODIFIER_ORDER]
        base_key = [p for p in parts if p not in MODIFIER_ORDER][0]

        mod_flags = _get_modifier_flags(mods)
        vk_code = _get_vk_code(base_key)
        if vk_code is None:
            err = f"Tecla no reconocida: '{base_key}'."
            self.registration_failed.emit(err)
            return False, err

        # Unregister previous hotkey before registering new one
        if self._is_registered:
            self.unregister_hotkey()

        success, err_code = self._thread.register_hotkey(self._hotkey_id, mod_flags, vk_code)
        if not success:
            logger.warning(
                f"Failed to register hotkey '{normalized}' (code: {err_code})"
            )
            conflict_msg = (
                "Esta combinación ya está siendo utilizada por otra aplicación o por Windows."
            )
            self._is_registered = False
            self._current_hotkey = ""
            self.registration_failed.emit(conflict_msg)
            return False, conflict_msg

        self._is_registered = True
        self._current_hotkey = normalized
        self._config_manager.set_hotkey(normalized)
        logger.info(f"Successfully registered hotkey: '{normalized}'")
        self.hotkey_registered.emit(normalized)
        return True, ""

    def unregister_hotkey(self) -> None:
        """Unregisters the current hotkey from Windows."""
        if self._is_registered:
            self._thread.unregister_hotkey(self._hotkey_id)
            logger.info(f"Unregistered hotkey: '{self._current_hotkey}'")
            self._is_registered = False
            self._current_hotkey = ""

    def update_hotkey(self, new_hotkey: str) -> tuple[bool, str]:
        """High-level shortcut to validate, register and persist a new hotkey."""
        return self.register_hotkey(new_hotkey)

    def get_current_hotkey(self) -> str:
        """Returns the currently active hotkey string, or empty string if none registered."""
        return self._current_hotkey

    def is_registered(self) -> bool:
        """Returns whether a hotkey is currently registered."""
        return self._is_registered

    def is_hotkey_available(self, hotkey_str: str) -> tuple[bool, str]:
        """
        Tests if a hotkey combination can be registered without permanently binding it.
        Returns (is_available, error_message).
        """
        is_valid, validation_msg = self.validate_hotkey(hotkey_str)
        if not is_valid:
            return False, validation_msg

        normalized = self.normalize_hotkey(hotkey_str)
        if normalized == self._current_hotkey and self._is_registered:
            return True, ""

        if sys.platform != "win32":
            return True, ""

        parts = normalized.split("+")
        mods = [p for p in parts if p in MODIFIER_ORDER]
        base_key = [p for p in parts if p not in MODIFIER_ORDER][0]

        mod_flags = _get_modifier_flags(mods)
        vk_code = _get_vk_code(base_key)
        if vk_code is None:
            return False, f"Tecla no reconocida: '{base_key}'."

        temp_id = 0xBEEF
        success, err_code = self._thread.register_hotkey(temp_id, mod_flags, vk_code)
        if not success:
            return False, "Esta combinación ya está siendo utilizada por otra aplicación o por Windows."

        self._thread.unregister_hotkey(temp_id)
        return True, ""

    def cleanup(self) -> None:
        """Stops the worker thread and releases resources."""
        self.unregister_hotkey()
        if self._thread and self._thread.is_alive():
            self._thread.stop()

    def __del__(self) -> None:
        try:
            self.cleanup()
        except Exception:
            pass

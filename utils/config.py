from typing import Optional
from PySide6.QtCore import QSettings

DEFAULT_HOTKEY = "Ctrl+Space"
DEFAULT_AUTO_PASTE = True
DEFAULT_AUTO_PAUSE_SECONDS = 1.5
DEFAULT_LANGUAGE = "es"
DEFAULT_MODEL_NAME = "base"
DEFAULT_OVERLAY_POSITION = "top"
DEFAULT_OVERLAY_SIZE = "normal"


class ConfigManager:
    """Manages application configuration with QSettings persistence."""

    def __init__(self, settings: Optional[QSettings] = None):
        if settings is not None:
            self._settings = settings
        else:
            self._settings = QSettings("DavidCaro", "VoiceDictation")

    # Hotkey
    def get_hotkey(self) -> str:
        val = self._settings.value("hotkey", DEFAULT_HOTKEY)
        return str(val) if val else DEFAULT_HOTKEY

    def set_hotkey(self, hotkey: str) -> None:
        self._settings.setValue("hotkey", hotkey)

    def restore_default_hotkey(self) -> None:
        self.set_hotkey(DEFAULT_HOTKEY)

    # Auto paste
    def get_auto_paste(self) -> bool:
        val = self._settings.value("auto_paste", DEFAULT_AUTO_PASTE)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)

    def set_auto_paste(self, enabled: bool) -> None:
        self._settings.setValue("auto_paste", bool(enabled))

    # Auto pause seconds
    def get_auto_pause_seconds(self) -> float:
        val = self._settings.value("auto_pause_seconds", DEFAULT_AUTO_PAUSE_SECONDS)
        try:
            return float(val)
        except (ValueError, TypeError):
            return DEFAULT_AUTO_PAUSE_SECONDS

    def set_auto_pause_seconds(self, val: float) -> None:
        self._settings.setValue("auto_pause_seconds", float(val))

    # Microphone index
    def get_microphone_index(self) -> Optional[int]:
        val = self._settings.value("microphone_index", None)
        if val is None or val == "" or str(val).lower() == "none":
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def set_microphone_index(self, idx: Optional[int]) -> None:
        if idx is None:
            self._settings.remove("microphone_index")
        else:
            self._settings.setValue("microphone_index", int(idx))

    # Language
    def get_language(self) -> str:
        val = self._settings.value("language", DEFAULT_LANGUAGE)
        return str(val) if val else DEFAULT_LANGUAGE

    def set_language(self, lang: str) -> None:
        self._settings.setValue("language", lang)

    # Model name
    def get_model_name(self) -> str:
        val = self._settings.value("model_name", DEFAULT_MODEL_NAME)
        return str(val) if val else DEFAULT_MODEL_NAME

    def set_model_name(self, name: str) -> None:
        self._settings.setValue("model_name", name)

    # Overlay position ("top" | "bottom")
    def get_overlay_position(self) -> str:
        val = self._settings.value("overlay_position", DEFAULT_OVERLAY_POSITION)
        return str(val) if val else DEFAULT_OVERLAY_POSITION

    def set_overlay_position(self, pos: str) -> None:
        self._settings.setValue("overlay_position", pos)

    # Overlay size ("normal" | "compact")
    def get_overlay_size(self) -> str:
        val = self._settings.value("overlay_size", DEFAULT_OVERLAY_SIZE)
        return str(val) if val else DEFAULT_OVERLAY_SIZE

    def set_overlay_size(self, sz: str) -> None:
        self._settings.setValue("overlay_size", sz)

    # First run onboarding
    def is_first_run(self) -> bool:
        val = self._settings.value("first_run_completed", False)
        if isinstance(val, bool):
            completed = val
        elif isinstance(val, str):
            completed = val.lower() in ("true", "1", "yes")
        else:
            completed = bool(val)
        return not completed

    def set_first_run_completed(self) -> None:
        self._settings.setValue("first_run_completed", True)

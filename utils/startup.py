"""Windows startup registry management for Voice Dictation."""

import os
import sys
from typing import Optional

from utils.logger import get_logger

logger = get_logger("utils.startup")

APP_NAME = "VoiceDictation"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_app_command() -> str:
    """Returns the executable command line for startup."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    main_script = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{main_script}"'


def is_startup_enabled(app_name: str = APP_NAME) -> bool:
    """Checks if the application is set to start with Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ
        ) as key:
            val, _ = winreg.QueryValueEx(key, app_name)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.debug(f"Error checking startup registry: {e}")
        return False


def set_startup_enabled(
    enabled: bool, app_name: str = APP_NAME, command: Optional[str] = None
) -> bool:
    """Enables or disables auto-start with Windows via HKCU Run registry."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                cmd = command or get_app_command()
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
                logger.info(f"Startup enabled for {app_name}: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    logger.info(f"Startup disabled for {app_name}")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        logger.warning(f"Error setting startup registry: {e}")
        return False

"""Clipboard management with Qt and pyperclip fallback.

Provides guaranteed UTF-8, accent, special character, and multiline support
for Windows clipboard operations.
"""

import logging
from typing import Optional
import pyperclip

logger = logging.getLogger(__name__)


class Clipboard:
    """Manages clipboard interactions with Qt and pyperclip fallbacks."""

    @staticmethod
    def _get_qt_clipboard():
        """Retrieve QClipboard if a QApplication or QGuiApplication is running."""
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QGuiApplication

            app = QApplication.instance() or QGuiApplication.instance()
            if app is not None:
                cb = app.clipboard()
                if cb is not None:
                    return cb
        except Exception as e:
            logger.debug(f"Qt clipboard not available: {e}")
        return None

    @staticmethod
    def copy(text: str) -> bool:
        """Copies text to the system clipboard.

        Prefers QApplication.clipboard() if an active Qt instance exists,
        with fallback to pyperclip.copy(). Guarantees support for full UTF-8,
        Spanish accents, ñ, special symbols, and multiline strings.

        Args:
            text: The text string to copy.

        Returns:
            True if text was successfully copied, False otherwise.
        """
        try:
            if not isinstance(text, str):
                text = str(text)

            qt_cb = Clipboard._get_qt_clipboard()
            if qt_cb is not None:
                try:
                    qt_cb.setText(text)
                    return True
                except Exception as e:
                    logger.warning(f"Qt clipboard setText failed, falling back to pyperclip: {e}")

            pyperclip.copy(text)
            return True
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}", exc_info=True)
            return False

    @staticmethod
    def get_text() -> str:
        """Retrieves the current text content from the clipboard.

        Returns:
            The text string currently in the clipboard, or empty string on error.
        """
        try:
            qt_cb = Clipboard._get_qt_clipboard()
            if qt_cb is not None:
                try:
                    return qt_cb.text()
                except Exception as e:
                    logger.warning(f"Qt clipboard get text failed, falling back to pyperclip: {e}")

            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Failed to retrieve text from clipboard: {e}", exc_info=True)
            return ""

    @staticmethod
    def clear() -> None:
        """Clears the contents of the system clipboard."""
        try:
            qt_cb = Clipboard._get_qt_clipboard()
            if qt_cb is not None:
                try:
                    qt_cb.clear()
                    return
                except Exception as e:
                    logger.warning(f"Qt clipboard clear failed, falling back to pyperclip: {e}")

            pyperclip.copy("")
        except Exception as e:
            logger.error(f"Failed to clear clipboard: {e}", exc_info=True)

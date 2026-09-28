"""Voice Dictation - Main Application Entrypoint."""

import sys
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from app.main_window import MainWindow
from utils.logger import setup_logger, get_logger

logger = get_logger("main")

MUTEX_NAME = "Global\\VoiceDictation_SingleInstance_Mutex"
ERROR_ALREADY_EXISTS = 183


def acquire_single_instance_mutex():
    """Acquires a named Win32 Mutex to prevent multiple concurrent instances.

    Returns the mutex handle if this is the only instance, or None if already running.
    """
    if sys.platform != "win32":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        create_mutex = ctypes.windll.kernel32.CreateMutexW
        create_mutex.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        create_mutex.restype = wintypes.HANDLE

        mutex = create_mutex(None, False, MUTEX_NAME)
        last_error = ctypes.windll.kernel32.GetLastError()

        if last_error == ERROR_ALREADY_EXISTS:
            logger.warning("Another instance of Voice Dictation is already running.")
            return None
        return mutex
    except Exception as e:
        logger.warning(f"Could not verify single-instance mutex: {e}")
        return None


def main() -> int:
    """Main execution function."""
    setup_logger()
    logger.info("Initializing Voice Dictation...")

    # Single-instance guard
    mutex = acquire_single_instance_mutex()
    if sys.platform == "win32" and mutex is None:
        # Create temporary app to notify user cleanly
        app = QApplication.instance() or QApplication(sys.argv)
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Voice Dictation")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText("Voice Dictation ya se encuentra en ejecución en la bandeja del sistema.")
        msg_box.exec()
        return 0

    # Ensure QApplication exists
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("Voice Dictation")
    app.setOrganizationName("DavidCaro")
    app.setQuitOnLastWindowClosed(False)

    # Initialize main coordinator
    main_window = MainWindow()
    main_window.start()

    logger.info("Application event loop running.")
    exit_code = app.exec()

    # Release single instance mutex if held
    if sys.platform == "win32" and mutex:
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(mutex)
        except Exception:
            pass

    logger.info(f"Application terminated with code {exit_code}.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

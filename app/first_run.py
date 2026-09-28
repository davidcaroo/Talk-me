"""First Run Wizard / Onboarding Dialog for Voice Dictation."""

from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QFrame,
    QWidget,
)

from app.widgets.hotkey_selector import HotkeySelector
from audio.devices import AudioDevices
from input.hotkey_manager import HotkeyManager
from utils.config import ConfigManager, DEFAULT_HOTKEY
from utils.logger import get_logger

logger = get_logger("app.first_run")

WIZARD_STYLE = """
QDialog {
    background-color: #16161A;
    color: #F5F5F7;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
}
QFrame#card {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 16px;
}
QLabel#header_title {
    font-size: 22px;
    font-weight: 700;
    color: #FFFFFF;
}
QLabel#header_subtitle {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.4;
}
QLabel#key_badge {
    background-color: rgba(10, 132, 255, 0.2);
    border: 1px solid rgba(10, 132, 255, 0.5);
    border-radius: 8px;
    color: #64D2FF;
    font-size: 18px;
    font-weight: 700;
    padding: 10px 20px;
}
QLabel#plus_label {
    font-size: 20px;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.5);
    padding: 0 6px;
}
QComboBox {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 8px;
    color: #FFFFFF;
    padding: 8px 12px;
    font-size: 13px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #1E1E24;
    color: #FFFFFF;
    selection-background-color: #0A84FF;
    selection-color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.15);
}
QCheckBox {
    color: rgba(255, 255, 255, 0.9);
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.3);
    background-color: rgba(255, 255, 255, 0.06);
}
QCheckBox::indicator:checked {
    background-color: #0A84FF;
    border-color: #0A84FF;
}
QPushButton#primary_button {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0A84FF, stop:1 #0071E3);
    border: none;
    border-radius: 10px;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 600;
    padding: 11px 24px;
}
QPushButton#primary_button:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #409CFF, stop:1 #0A84FF);
}
QPushButton#secondary_button {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 10px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 500;
    padding: 9px 18px;
}
QPushButton#secondary_button:hover {
    background-color: rgba(255, 255, 255, 0.15);
}
QLabel#privacy_badge {
    color: #30D158;
    font-size: 12px;
    font-weight: 600;
}
"""


class FirstRunWizard(QDialog):
    """First-run onboarding experience showcasing the default hotkey,

    microphone selection, auto-paste toggle, and privacy guarantees.
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        hotkey_manager: Optional[HotkeyManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._config_manager = config_manager or ConfigManager()
        self._hotkey_manager = hotkey_manager
        self._selected_hotkey = self._config_manager.get_hotkey() or DEFAULT_HOTKEY

        self.setWindowTitle("Bienvenido a Voice Dictation")
        self.setMinimumWidth(540)
        self.setModal(True)
        self.setStyleSheet(WIZARD_STYLE)

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(18)

        # Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)
        title = QLabel("Voice Dictation", self)
        title.setObjectName("header_title")
        header_layout.addWidget(title)

        subtitle = QLabel(
            "Tu atajo recomendado es Ctrl + Space.\n"
            "Presiónalo en cualquier aplicación para empezar a dictar y vuelve a presionarlo para terminar.",
            self,
        )
        subtitle.setObjectName("header_subtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)

        # Recommended Hotkey Banner Card
        self._hotkey_card = QFrame(self)
        self._hotkey_card.setObjectName("card")
        card_layout = QVBoxLayout(self._hotkey_card)
        card_layout.setSpacing(12)

        # Badges row
        self._badges_row = QHBoxLayout()
        self._badges_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._build_key_badges(self._selected_hotkey)
        card_layout.addLayout(self._badges_row)

        # Buttons row for Hotkey (Use recommended vs Change)
        hk_btn_layout = QHBoxLayout()
        hk_btn_layout.setSpacing(10)
        hk_btn_layout.addStretch()

        self._btn_change_hotkey = QPushButton("Cambiar atajo...", self._hotkey_card)
        self._btn_change_hotkey.setObjectName("secondary_button")
        self._btn_change_hotkey.clicked.connect(self._toggle_hotkey_selector)
        hk_btn_layout.addWidget(self._btn_change_hotkey)

        hk_btn_layout.addStretch()
        card_layout.addLayout(hk_btn_layout)

        # Embedded HotkeySelector (initially hidden)
        self._hotkey_selector = HotkeySelector(
            hotkey_manager=self._hotkey_manager,
            config_manager=self._config_manager,
            parent=self._hotkey_card,
        )
        self._hotkey_selector.setVisible(False)
        self._hotkey_selector.hotkey_saved.connect(self._on_custom_hotkey_saved)
        card_layout.addWidget(self._hotkey_selector)

        layout.addWidget(self._hotkey_card)

        # Configuration Options Card (Microphone & Auto-paste)
        options_card = QFrame(self)
        options_card.setObjectName("card")
        opts_layout = QVBoxLayout(options_card)
        opts_layout.setSpacing(12)

        # Microphone selector
        mic_label = QLabel("Micrófono de entrada:", options_card)
        mic_label.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-weight: 600; font-size: 13px;")
        opts_layout.addWidget(mic_label)

        self._mic_combo = QComboBox(options_card)
        self._populate_microphones()
        opts_layout.addWidget(self._mic_combo)

        # Auto-paste checkbox
        self._auto_paste_check = QCheckBox("Pegar automáticamente el texto transcrito (Ctrl + V)", options_card)
        self._auto_paste_check.setChecked(self._config_manager.get_auto_paste())
        opts_layout.addWidget(self._auto_paste_check)

        layout.addWidget(options_card)

        # Privacy Badges Banner
        privacy_label = QLabel("✓ 100% Local   ✓ Sin suscripción   ✓ Privacidad total", self)
        privacy_label.setObjectName("privacy_badge")
        privacy_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(privacy_label)

        # Action Buttons (Start using Voice Dictation)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self._btn_start = QPushButton("¡Listo! Comenzar a dictar", self)
        self._btn_start.setObjectName("primary_button")
        self._btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_start.clicked.connect(self._on_finish)
        bottom_layout.addWidget(self._btn_start)

        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)

    def _build_key_badges(self, hotkey_str: str) -> None:
        """Draws large keyboard badges for the hotkey."""
        while self._badges_row.count():
            item = self._badges_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        parts = [p.strip() for p in hotkey_str.split("+") if p.strip()]
        for idx, part in enumerate(parts):
            badge = QLabel(part, self._hotkey_card)
            badge.setObjectName("key_badge")
            self._badges_row.addWidget(badge)

            if idx < len(parts) - 1:
                plus = QLabel("+", self._hotkey_card)
                plus.setObjectName("plus_label")
                self._badges_row.addWidget(plus)

    def _toggle_hotkey_selector(self) -> None:
        """Shows or hides the interactive hotkey selector."""
        currently_hidden = self._hotkey_selector.isHidden()
        self._hotkey_selector.setVisible(currently_hidden)
        if currently_hidden:
            self._btn_change_hotkey.setText("Ocultar selector de atajo")
        else:
            self._btn_change_hotkey.setText("Cambiar atajo...")
        self.adjustSize()

    def _on_custom_hotkey_saved(self, new_hotkey: str) -> None:
        """Updates internal hotkey when saved in HotkeySelector."""
        self._selected_hotkey = new_hotkey
        self._build_key_badges(new_hotkey)
        self._hotkey_selector.setVisible(False)
        self._btn_change_hotkey.setText("Cambiar atajo...")
        self.adjustSize()

    def _populate_microphones(self) -> None:
        """Fills mic combobox with available hardware input devices."""
        self._mic_combo.clear()
        devices = AudioDevices.get_input_devices()

        self._mic_combo.addItem("Micrófono predeterminado del sistema", userData=None)

        current_saved_idx = self._config_manager.get_microphone_index()
        selected_combo_idx = 0

        for i, dev in enumerate(devices):
            dev_idx = dev.get("index")
            dev_name = dev.get("name", f"Microphone {dev_idx}")
            self._mic_combo.addItem(f"{dev_name} (Dispositivo {dev_idx})", userData=dev_idx)
            if current_saved_idx is not None and dev_idx == current_saved_idx:
                selected_combo_idx = i + 1

        self._mic_combo.setCurrentIndex(selected_combo_idx)

    def _on_finish(self) -> None:
        """Saves choices to ConfigManager and closes wizard."""
        # Save Hotkey
        self._config_manager.set_hotkey(self._selected_hotkey)
        if self._hotkey_manager:
            self._hotkey_manager.update_hotkey(self._selected_hotkey)

        # Save Microphone
        mic_idx = self._mic_combo.currentData()
        self._config_manager.set_microphone_index(mic_idx)

        # Save Auto-paste
        self._config_manager.set_auto_paste(self._auto_paste_check.isChecked())

        # Complete first run
        self._config_manager.set_first_run_completed()
        logger.info(
            f"First run wizard completed: hotkey={self._selected_hotkey}, "
            f"mic={mic_idx}, auto_paste={self._auto_paste_check.isChecked()}"
        )

        self.accept()

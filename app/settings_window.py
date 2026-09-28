"""Multi-tab Settings Dialog for Voice Dictation."""

from typing import Optional, Callable
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QComboBox,
    QCheckBox,
    QSlider,
    QPushButton,
    QFrame,
    QFormLayout,
)

from app.widgets.hotkey_selector import HotkeySelector
from audio.devices import AudioDevices
from input.hotkey_manager import HotkeyManager
from utils.config import ConfigManager
from utils.logger import get_logger
from utils.startup import is_startup_enabled, set_startup_enabled

logger = get_logger("app.settings_window")

SETTINGS_STYLE = """
QDialog {
    background-color: #16161A;
    color: #F5F5F7;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
}
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    background-color: rgba(28, 28, 34, 0.7);
    top: -1px;
}
QTabBar::tab {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    color: rgba(255, 255, 255, 0.7);
    padding: 8px 18px;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: rgba(28, 28, 34, 0.95);
    border-color: rgba(255, 255, 255, 0.2);
    color: #FFFFFF;
    font-weight: 600;
}
QTabBar::tab:hover:!selected {
    background-color: rgba(255, 255, 255, 0.1);
    color: #FFFFFF;
}
QFrame#section_card {
    background-color: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    padding: 12px;
}
QLabel {
    color: #F5F5F7;
    font-size: 13px;
}
QLabel#header_title {
    font-size: 18px;
    font-weight: 700;
    color: #FFFFFF;
}
QLabel#section_heading {
    font-size: 14px;
    font-weight: 600;
    color: #64D2FF;
}
QLabel#hint_text {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.55);
}
QComboBox {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 8px;
    color: #FFFFFF;
    padding: 6px 12px;
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
QSlider::groove:horizontal {
    height: 6px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #0A84FF;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 1px solid rgba(0, 0, 0, 0.2);
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QPushButton#primary_button {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0A84FF, stop:1 #0071E3);
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 20px;
}
QPushButton#primary_button:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #409CFF, stop:1 #0A84FF);
}
QPushButton#secondary_button {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 8px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 16px;
}
QPushButton#secondary_button:hover {
    background-color: rgba(255, 255, 255, 0.14);
}
"""


class SettingsWindow(QDialog):
    """Configuration Dialog covering General, Dictation, Appearance, and About settings."""

    settings_updated = Signal()

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        hotkey_manager: Optional[HotkeyManager] = None,
        parent: Optional[QWidget] = None,
        initial_tab: str = "general",
    ):
        super().__init__(parent)
        self._config_manager = config_manager or ConfigManager()
        self._hotkey_manager = hotkey_manager

        self.setWindowTitle("Configuración - Voice Dictation")
        self.setMinimumSize(560, 480)
        self.setStyleSheet(SETTINGS_STYLE)

        self._init_ui()
        self.select_tab(initial_tab)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Tab widget
        self._tabs = QTabWidget(self)

        # Tabs creation
        self._tab_general = self._create_general_tab()
        self._tab_dictation = self._create_dictation_tab()
        self._tab_appearance = self._create_appearance_tab()
        self._tab_about = self._create_about_tab()

        self._tabs.addTab(self._tab_general, "General")
        self._tabs.addTab(self._tab_dictation, "Dictado")
        self._tabs.addTab(self._tab_appearance, "Apariencia")
        self._tabs.addTab(self._tab_about, "Acerca de")

        main_layout.addWidget(self._tabs)

        # Bottom Buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self._btn_close = QPushButton("Cerrar", self)
        self._btn_close.setObjectName("primary_button")
        self._btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(self._btn_close)

        main_layout.addLayout(bottom_layout)

    # =========================================================================
    # Tab 1: GENERAL
    # =========================================================================
    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        card = QFrame(widget)
        card.setObjectName("section_card")
        form = QFormLayout(card)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # Microphone Selector
        self._mic_combo = QComboBox(card)
        self._populate_microphones()
        self._mic_combo.currentIndexChanged.connect(self._on_mic_changed)
        form.addRow("Micrófono:", self._mic_combo)

        # Language Selector
        self._lang_combo = QComboBox(card)
        self._lang_combo.addItem("Español (es)", "es")
        self._lang_combo.addItem("English (en)", "en")
        self._lang_combo.addItem("Français (fr)", "fr")
        self._lang_combo.addItem("Deutsch (de)", "de")
        self._lang_combo.addItem("Italiano (it)", "it")
        self._lang_combo.addItem("Português (pt)", "pt")

        current_lang = self._config_manager.get_language()
        for idx in range(self._lang_combo.count()):
            if self._lang_combo.itemData(idx) == current_lang:
                self._lang_combo.setCurrentIndex(idx)
                break
        self._lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        form.addRow("Idioma de dictado:", self._lang_combo)

        # Auto-paste Checkbox
        self._auto_paste_check = QCheckBox("Pegar automáticamente el texto (Ctrl + V)", card)
        self._auto_paste_check.setChecked(self._config_manager.get_auto_paste())
        self._auto_paste_check.toggled.connect(self._on_auto_paste_toggled)
        form.addRow("", self._auto_paste_check)

        # Start with Windows Checkbox
        self._startup_check = QCheckBox("Iniciar automáticamente con Windows", card)
        self._startup_check.setChecked(is_startup_enabled())
        self._startup_check.toggled.connect(self._on_startup_toggled)
        form.addRow("", self._startup_check)

        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _populate_microphones(self) -> None:
        self._mic_combo.clear()
        self._mic_combo.addItem("Predeterminado del sistema", userData=None)

        devices = AudioDevices.get_input_devices()
        current_idx = self._config_manager.get_microphone_index()
        active_pos = 0

        for i, dev in enumerate(devices):
            d_idx = dev.get("index")
            d_name = dev.get("name", f"Microphone {d_idx}")
            self._mic_combo.addItem(f"{d_name} (#{d_idx})", userData=d_idx)
            if current_idx is not None and d_idx == current_idx:
                active_pos = i + 1

        self._mic_combo.setCurrentIndex(active_pos)

    def _on_mic_changed(self) -> None:
        dev_idx = self._mic_combo.currentData()
        self._config_manager.set_microphone_index(dev_idx)
        logger.info(f"Microphone changed to index: {dev_idx}")
        self.settings_updated.emit()

    def _on_lang_changed(self) -> None:
        lang = self._lang_combo.currentData()
        if lang:
            self._config_manager.set_language(lang)
            logger.info(f"Language changed to: {lang}")
            self.settings_updated.emit()

    def _on_auto_paste_toggled(self, checked: bool) -> None:
        self._config_manager.set_auto_paste(checked)
        logger.info(f"Auto paste toggled: {checked}")
        self.settings_updated.emit()

    def _on_startup_toggled(self, checked: bool) -> None:
        set_startup_enabled(checked)
        logger.info(f"Startup with Windows toggled: {checked}")
        self.settings_updated.emit()

    # =========================================================================
    # Tab 2: DICTADO
    # =========================================================================
    def _create_dictation_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Hotkey selector widget
        self._hotkey_selector = HotkeySelector(
            hotkey_manager=self._hotkey_manager,
            config_manager=self._config_manager,
            parent=widget,
        )
        self._hotkey_selector.hotkey_saved.connect(self._on_hotkey_saved)
        layout.addWidget(self._hotkey_selector)

        # Dictation timing and model options card
        card = QFrame(widget)
        card.setObjectName("section_card")
        form = QFormLayout(card)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # Auto-pause seconds slider (1.0s to 3.0s, step 0.1s -> 10 to 30)
        pause_row = QHBoxLayout()
        current_pause = self._config_manager.get_auto_pause_seconds()
        self._slider_pause = QSlider(Qt.Orientation.Horizontal, card)
        self._slider_pause.setRange(10, 30)
        self._slider_pause.setValue(int(round(current_pause * 10)))

        self._lbl_pause_val = QLabel(f"{current_pause:.1f} s", card)
        self._lbl_pause_val.setStyleSheet("font-weight: 600; color: #64D2FF; min-width: 40px;")
        self._slider_pause.valueChanged.connect(self._on_pause_slider_changed)

        pause_row.addWidget(self._slider_pause)
        pause_row.addWidget(self._lbl_pause_val)
        form.addRow("Tiempo de auto-pausa:", pause_row)

        hint_pause = QLabel("Tiempo de silencio antes de pausar temporalmente la captura.", card)
        hint_pause.setObjectName("hint_text")
        form.addRow("", hint_pause)

        # Whisper Model Selector
        self._model_combo = QComboBox(card)
        self._model_combo.addItem("base (Recomendado - Rápido y preciso)", "base")
        self._model_combo.addItem("small (Mayor precisión - Requiere más CPU)", "small")
        self._model_combo.addItem("tiny (Ultra ligero)", "tiny")

        current_model = self._config_manager.get_model_name()
        for idx in range(self._model_combo.count()):
            if self._model_combo.itemData(idx) == current_model:
                self._model_combo.setCurrentIndex(idx)
                break
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        form.addRow("Modelo Whisper:", self._model_combo)

        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _on_hotkey_saved(self, new_hotkey: str) -> None:
        logger.info(f"Hotkey updated in settings: {new_hotkey}")
        self.settings_updated.emit()

    def _on_pause_slider_changed(self, value: int) -> None:
        seconds = value / 10.0
        self._lbl_pause_val.setText(f"{seconds:.1f} s")
        self._config_manager.set_auto_pause_seconds(seconds)
        self.settings_updated.emit()

    def _on_model_changed(self) -> None:
        model = self._model_combo.currentData()
        if model:
            self._config_manager.set_model_name(model)
            logger.info(f"Whisper model changed to: {model}")
            self.settings_updated.emit()

    # =========================================================================
    # Tab 3: APARIENCIA
    # =========================================================================
    def _create_appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        card = QFrame(widget)
        card.setObjectName("section_card")
        form = QFormLayout(card)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # Overlay position (Superior / Inferior)
        self._pos_combo = QComboBox(card)
        self._pos_combo.addItem("Superior (Top)", "top")
        self._pos_combo.addItem("Inferior (Bottom)", "bottom")

        curr_pos = self._config_manager.get_overlay_position()
        self._pos_combo.setCurrentIndex(1 if curr_pos.lower() == "bottom" else 0)
        self._pos_combo.currentIndexChanged.connect(self._on_position_changed)
        form.addRow("Posición del overlay:", self._pos_combo)

        # Overlay size (Normal / Compacto)
        self._size_combo = QComboBox(card)
        self._size_combo.addItem("Normal", "normal")
        self._size_combo.addItem("Compacto", "compact")

        curr_size = self._config_manager.get_overlay_size()
        self._size_combo.setCurrentIndex(1 if curr_size.lower() == "compact" else 0)
        self._size_combo.currentIndexChanged.connect(self._on_size_changed)
        form.addRow("Tamaño del overlay:", self._size_combo)

        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _on_position_changed(self) -> None:
        pos = self._pos_combo.currentData()
        self._config_manager.set_overlay_position(pos)
        logger.info(f"Overlay position changed to: {pos}")
        self.settings_updated.emit()

    def _on_size_changed(self) -> None:
        sz = self._size_combo.currentData()
        self._config_manager.set_overlay_size(sz)
        logger.info(f"Overlay size changed to: {sz}")
        self.settings_updated.emit()

    # =========================================================================
    # Tab 4: ACERCA DE
    # =========================================================================
    def _create_about_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        card = QFrame(widget)
        card.setObjectName("section_card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        app_title = QLabel("Voice Dictation", card)
        app_title.setObjectName("header_title")
        card_layout.addWidget(app_title)

        version_lbl = QLabel("Versión: v1.0.0", card)
        version_lbl.setStyleSheet("color: #64D2FF; font-weight: 600;")
        card_layout.addWidget(version_lbl)

        desc_lbl = QLabel(
            "Utility de dictado global para Windows con transcripción local y activación mediante atajos personalizables.",
            card,
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.85); line-height: 1.4;")
        card_layout.addWidget(desc_lbl)

        sep = QFrame(card)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); margin: 6px 0;")
        card_layout.addWidget(sep)

        dev_lbl = QLabel("Desarrollado por: David Caro (@ing.davidcaro)", card)
        dev_lbl.setStyleSheet("font-weight: 500; color: #FFFFFF;")
        card_layout.addWidget(dev_lbl)

        badges_lbl = QLabel("✓ 100% Local   ✓ Privacidad Total   ✓ faster-whisper", card)
        badges_lbl.setStyleSheet("color: #30D158; font-size: 12px; font-weight: 600;")
        card_layout.addWidget(badges_lbl)

        layout.addWidget(card)
        layout.addStretch()
        return widget

    def select_tab(self, tab_name: str) -> None:
        """Selects tab by name: 'general', 'dictation', 'appearance', 'about'."""
        mapping = {
            "general": 0,
            "dictation": 1,
            "dictado": 1,
            "appearance": 2,
            "apariencia": 2,
            "about": 3,
            "acerca": 3,
        }
        idx = mapping.get(str(tab_name).lower(), 0)
        self._tabs.setCurrentIndex(idx)

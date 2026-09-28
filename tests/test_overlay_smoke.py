"""Smoke and unit tests for FloatingOverlay and visionOS widgets."""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt, QSettings, QPoint, QRect
from PySide6.QtGui import QKeyEvent, QGuiApplication, QScreen
from PySide6.QtWidgets import QApplication

from models.app_state import AppState
from utils.config import ConfigManager
from controllers.dictation_controller import DictationController
from app.widgets.waveform_view import WaveformView
from app.widgets.status_badge import StatusBadge
from app.widgets.dictation_bar import DictationBar
from app.overlay import FloatingOverlay


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_config(tmp_path):
    settings_file = str(tmp_path / "test_overlay_settings.ini")
    settings = QSettings(settings_file, QSettings.Format.IniFormat)
    settings.clear()
    return ConfigManager(settings)


@pytest.fixture
def mock_controller():
    controller = MagicMock(spec=DictationController)
    controller.current_hotkey = "Ctrl+Space"
    controller.state = AppState.IDLE
    # Create real signals or mocks for dictation controller
    from PySide6.QtCore import QObject, Signal

    class DummySignalEmitter(QObject):
        state_changed = Signal(AppState)
        amplitude_updated = Signal(float)
        status_text_updated = Signal(str)
        subtext_updated = Signal(str)

    emitter = DummySignalEmitter()
    controller._emitter = emitter
    controller.state_changed = emitter.state_changed
    controller.amplitude_updated = emitter.amplitude_updated
    controller.status_text_updated = emitter.status_text_updated
    controller.subtext_updated = emitter.subtext_updated
    controller.cancel_dictation = MagicMock()
    return controller


class TestWaveformView:
    def test_init_and_properties(self, qapp):
        waveform = WaveformView(bar_count=6)
        assert waveform.bar_count == 6
        assert waveform.amplitude == 0.0
        assert waveform.state == AppState.IDLE

    def test_amplitude_clamping(self, qapp):
        waveform = WaveformView()
        waveform.set_amplitude(1.5)
        assert waveform.amplitude <= 1.0
        waveform.set_amplitude(-0.5)
        assert waveform.amplitude >= 0.0

    def test_state_transitions(self, qapp):
        waveform = WaveformView()
        for state in [
            AppState.LISTENING,
            AppState.PAUSED,
            AppState.TRANSCRIBING,
            AppState.PASTING,
            AppState.DONE,
            AppState.ERROR,
            AppState.IDLE,
        ]:
            waveform.set_state(state)
            assert waveform.state == state

    def test_render_paint_event(self, qapp):
        waveform = WaveformView()
        waveform.resize(100, 32)
        # Calling repaint/render to ensure paintEvent doesn't crash in all states
        for state in [AppState.LISTENING, AppState.PAUSED, AppState.TRANSCRIBING, AppState.DONE]:
            waveform.set_state(state)
            waveform.set_amplitude(0.5)
            waveform.repaint()


class TestStatusBadge:
    def test_init_and_state_change(self, qapp):
        badge = StatusBadge()
        assert badge.state == AppState.IDLE
        for state in [
            AppState.LISTENING,
            AppState.PAUSED,
            AppState.TRANSCRIBING,
            AppState.DONE,
            AppState.ERROR,
            AppState.IDLE,
        ]:
            badge.set_state(state)
            assert badge.state == state
            badge.repaint()


class TestDictationBar:
    def test_init_and_subwidgets(self, qapp):
        bar = DictationBar()
        assert bar.waveform is not None
        assert bar.badge is not None
        assert bar.title_label is not None
        assert bar.subtitle_label is not None

    def test_setters(self, qapp):
        bar = DictationBar()
        bar.set_title("Escuchando...")
        assert bar.title_label.text() == "Escuchando..."
        bar.set_subtitle("Ctrl+Space para finalizar")
        assert bar.subtitle_label.text() == "Ctrl+Space para finalizar"

        bar.set_state(AppState.LISTENING)
        assert bar.waveform.state == AppState.LISTENING
        assert bar.badge.state == AppState.LISTENING

        bar.set_amplitude(0.7)
        assert bar.waveform.amplitude == pytest.approx(0.7, 0.05)

    def test_compact_mode(self, qapp):
        bar = DictationBar()
        bar.set_compact(True)
        assert bar.is_compact is True
        bar.set_compact(False)
        assert bar.is_compact is False


class TestFloatingOverlay:
    def test_window_flags_and_attributes(self, qapp, mock_controller, temp_config):
        overlay = FloatingOverlay(controller=mock_controller, config_manager=temp_config)
        flags = overlay.windowFlags()

        assert bool(flags & Qt.FramelessWindowHint)
        assert bool(flags & Qt.WindowStaysOnTopHint)
        assert bool(flags & Qt.Tool)
        assert bool(flags & Qt.WindowDoesNotAcceptFocus)

        assert overlay.testAttribute(Qt.WA_TranslucentBackground)
        assert overlay.testAttribute(Qt.WA_ShowWithoutActivating)

    def test_escape_key_cancels_dictation(self, qapp, mock_controller, temp_config):
        overlay = FloatingOverlay(controller=mock_controller, config_manager=temp_config)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        overlay.keyPressEvent(event)
        mock_controller.cancel_dictation.assert_called_once()

    def test_overlay_position_top(self, qapp, mock_controller, temp_config):
        temp_config.set_overlay_position("top")
        overlay = FloatingOverlay(controller=mock_controller, config_manager=temp_config)
        overlay.reposition()
        
        # Verify y position is near top (approx 50-80px from top of screen)
        screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        expected_y = screen_geo.top() + 60
        assert abs(overlay.y() - expected_y) < 30

    def test_overlay_position_bottom(self, qapp, mock_controller, temp_config):
        temp_config.set_overlay_position("bottom")
        overlay = FloatingOverlay(controller=mock_controller, config_manager=temp_config)
        overlay.reposition()

        screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        expected_y = screen_geo.bottom() - overlay.height() - 80
        assert abs(overlay.y() - expected_y) < 30

    def test_overlay_size_compact_and_normal(self, qapp, mock_controller, temp_config):
        temp_config.set_overlay_size("compact")
        overlay_compact = FloatingOverlay(controller=mock_controller, config_manager=temp_config)
        assert overlay_compact.dictation_bar.is_compact is True

        temp_config.set_overlay_size("normal")
        overlay_normal = FloatingOverlay(controller=mock_controller, config_manager=temp_config)
        assert overlay_normal.dictation_bar.is_compact is False

    def test_controller_signals_update_ui(self, qapp, mock_controller, temp_config):
        overlay = FloatingOverlay(controller=mock_controller, config_manager=temp_config)
        
        # Emit state change
        mock_controller.state_changed.emit(AppState.LISTENING)
        assert overlay.dictation_bar.badge.state == AppState.LISTENING

        # Emit title and subtext
        mock_controller.status_text_updated.emit("Hablando...")
        assert overlay.dictation_bar.title_label.text() == "Hablando..."

        mock_controller.subtext_updated.emit("Pausa si dejas de hablar")
        assert overlay.dictation_bar.subtitle_label.text() == "Pausa si dejas de hablar"

        # Emit amplitude
        mock_controller.amplitude_updated.emit(0.85)
        assert overlay.dictation_bar.waveform.amplitude == pytest.approx(0.85, 0.05)

    def test_fade_animation(self, qapp, mock_controller, temp_config):
        overlay = FloatingOverlay(controller=mock_controller, config_manager=temp_config)
        overlay.show_overlay()
        assert overlay.fade_animation is not None
        overlay.hide_overlay()
        assert overlay.fade_animation is not None

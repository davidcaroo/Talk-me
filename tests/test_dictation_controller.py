"""Unit tests for DictationController (Task 7)."""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

from models.app_state import AppState
from models.transcription_result import TranscriptionResult
from utils.config import DEFAULT_HOTKEY, ConfigManager
from input.clipboard import Clipboard
from input.paste import Paster
from audio.recorder import AudioRecorder
from input.hotkey_manager import HotkeyManager
from controllers.dictation_controller import DictationController


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication instance exists for Qt Signal and Timer tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock(spec=ConfigManager)
    config.get_hotkey.return_value = "Ctrl+Space"
    config.get_auto_paste.return_value = True
    config.get_microphone_index.return_value = 1
    config.get_model_name.return_value = "base"
    config.get_language.return_value = "es"
    return config


@pytest.fixture
def mock_recorder():
    recorder = MagicMock(spec=AudioRecorder)
    recorder.sample_rate = 16000
    recorder.start.return_value = True
    # Default 1 second of audio
    recorder.stop.return_value = np.zeros(16000, dtype=np.float32)
    recorder.is_recording.return_value = False
    return recorder


@pytest.fixture
def mock_hotkey_manager():
    hm = MagicMock(spec=HotkeyManager)
    hm.get_current_hotkey.return_value = "Ctrl+Space"
    hm.update_hotkey.return_value = (True, "")
    return hm


@pytest.fixture
def mock_clipboard():
    cb = MagicMock(spec=Clipboard)
    cb.copy.return_value = True
    return cb


@pytest.fixture
def mock_paster():
    paster = MagicMock(spec=Paster)
    paster.paste_clipboard.return_value = True
    return paster


@pytest.fixture
def controller(qapp, mock_config, mock_hotkey_manager, mock_recorder, mock_clipboard, mock_paster):
    ctrl = DictationController(
        config_manager=mock_config,
        hotkey_manager=mock_hotkey_manager,
        audio_recorder=mock_recorder,
        clipboard=mock_clipboard,
        paster=mock_paster,
    )
    return ctrl


class TestDictationControllerLifecycle:
    """Tests session lifecycle and state transitions."""

    def test_initial_state(self, controller):
        assert controller.state == AppState.IDLE
        assert controller.current_hotkey == "Ctrl+Space"

    def test_toggle_dictation_idle_to_listening(self, controller, mock_recorder, mock_config):
        state_changes = []
        status_texts = []
        subtexts = []

        controller.state_changed.connect(state_changes.append)
        controller.status_text_updated.connect(status_texts.append)
        controller.subtext_updated.connect(subtexts.append)

        controller.toggle_dictation()

        mock_recorder.start.assert_called_once_with(device_index=1)
        assert controller.state == AppState.LISTENING
        assert state_changes == [AppState.LISTENING]
        assert "Escuchando" in status_texts[-1]
        assert "Ctrl+Space para finalizar" in subtexts[-1]

    def test_toggle_dictation_recorder_start_failure(self, controller, mock_recorder):
        mock_recorder.start.return_value = False
        state_changes = []
        errors = []

        controller.state_changed.connect(state_changes.append)
        controller.session_error.connect(errors.append)

        controller.toggle_dictation()

        assert controller.state == AppState.ERROR
        assert AppState.ERROR in state_changes
        assert len(errors) > 0

    def test_toggle_dictation_short_audio_returns_to_idle(self, controller, mock_recorder):
        controller.toggle_dictation()
        assert controller.state == AppState.LISTENING

        # Return audio shorter than 0.2s (e.g. 0.1s = 1600 samples at 16kHz)
        mock_recorder.stop.return_value = np.zeros(1600, dtype=np.float32)

        state_changes = []
        controller.state_changed.connect(state_changes.append)

        with patch.object(controller, "_spawn_worker") as mock_spawn:
            controller.toggle_dictation()

            mock_recorder.stop.assert_called_once()
            mock_spawn.assert_not_called()
            assert controller.state == AppState.IDLE
            assert state_changes == [AppState.TRANSCRIBING, AppState.IDLE]

    def test_toggle_dictation_empty_audio_returns_to_idle(self, controller, mock_recorder):
        controller.toggle_dictation()
        assert controller.state == AppState.LISTENING

        mock_recorder.stop.return_value = np.zeros(0, dtype=np.float32)

        with patch.object(controller, "_spawn_worker") as mock_spawn:
            controller.toggle_dictation()
            mock_spawn.assert_not_called()
            assert controller.state == AppState.IDLE

    def test_toggle_dictation_listening_to_transcribing_valid_audio(self, controller, mock_recorder):
        controller.toggle_dictation()
        assert controller.state == AppState.LISTENING

        valid_audio = np.zeros(32000, dtype=np.float32)  # 2.0s
        mock_recorder.stop.return_value = valid_audio

        with patch.object(controller, "_spawn_worker") as mock_spawn:
            controller.toggle_dictation()

            assert controller.state == AppState.TRANSCRIBING
            mock_spawn.assert_called_once_with(valid_audio)

    def test_double_toggle_ignored_during_transcribing_and_pasting(self, controller, mock_recorder):
        controller.toggle_dictation()
        assert controller.state == AppState.LISTENING

        with patch.object(controller, "_spawn_worker"):
            controller.toggle_dictation()
            assert controller.state == AppState.TRANSCRIBING

        mock_recorder.start.reset_mock()
        mock_recorder.stop.reset_mock()

        # Try to toggle again while TRANSCRIBING
        controller.toggle_dictation()
        mock_recorder.start.assert_not_called()
        mock_recorder.stop.assert_not_called()
        assert controller.state == AppState.TRANSCRIBING

        # Set state to PASTING and verify toggle is ignored
        controller._state = AppState.PASTING
        controller.toggle_dictation()
        mock_recorder.start.assert_not_called()
        mock_recorder.stop.assert_not_called()
        assert controller.state == AppState.PASTING


class TestDictationControllerVAD:
    """Tests auto-pause and resume behavior with VAD events."""

    def test_silence_detected_pauses_when_listening(self, controller):
        controller.toggle_dictation()
        assert controller.state == AppState.LISTENING

        status_texts = []
        subtexts = []
        controller.status_text_updated.connect(status_texts.append)
        controller.subtext_updated.connect(subtexts.append)

        controller.on_silence_detected(1.5)

        assert controller.state == AppState.PAUSED
        assert "pausa" in status_texts[-1].lower()
        assert "Ctrl+Space" in subtexts[-1]

    def test_speech_detected_resumes_when_paused(self, controller):
        controller.toggle_dictation()
        controller.on_silence_detected(1.5)
        assert controller.state == AppState.PAUSED

        status_texts = []
        subtexts = []
        controller.status_text_updated.connect(status_texts.append)
        controller.subtext_updated.connect(subtexts.append)

        controller.on_speech_detected()

        assert controller.state == AppState.LISTENING
        assert "Escuchando" in status_texts[-1]
        assert "Ctrl+Space para finalizar" in subtexts[-1]

    def test_vad_ignored_when_idle(self, controller):
        assert controller.state == AppState.IDLE

        controller.on_silence_detected(1.5)
        assert controller.state == AppState.IDLE

        controller.on_speech_detected()
        assert controller.state == AppState.IDLE

    def test_toggle_dictation_from_paused_proceeds_to_transcribe(self, controller, mock_recorder):
        controller.toggle_dictation()
        controller.on_silence_detected(1.5)
        assert controller.state == AppState.PAUSED

        valid_audio = np.zeros(16000, dtype=np.float32)
        mock_recorder.stop.return_value = valid_audio

        with patch.object(controller, "_spawn_worker") as mock_spawn:
            controller.toggle_dictation()
            assert controller.state == AppState.TRANSCRIBING
            mock_spawn.assert_called_once_with(valid_audio)


class TestDictationControllerTranscription:
    """Tests transcription result handling, pasting, and error handling."""

    def test_transcription_finished_with_auto_paste(self, controller, mock_clipboard, mock_paster):
        controller._state = AppState.TRANSCRIBING

        inserted_texts = []
        status_texts = []
        state_changes = []
        controller.text_inserted.connect(inserted_texts.append)
        controller.status_text_updated.connect(status_texts.append)
        controller.state_changed.connect(state_changes.append)

        result = TranscriptionResult(text="Hola mundo dictado", duration=1.2, success=True)
        controller.on_transcription_finished(result)

        mock_clipboard.copy.assert_called_once_with("Hola mundo dictado")
        mock_paster.paste_clipboard.assert_called_once()
        assert controller.state == AppState.DONE
        assert AppState.PASTING in state_changes
        assert AppState.DONE in state_changes
        assert inserted_texts == ["Hola mundo dictado"]
        assert "insertado" in status_texts[-1].lower()

    def test_transcription_finished_without_auto_paste(self, controller, mock_config, mock_clipboard, mock_paster):
        mock_config.get_auto_paste.return_value = False
        controller._state = AppState.TRANSCRIBING

        state_changes = []
        controller.state_changed.connect(state_changes.append)

        result = TranscriptionResult(text="Texto copiado sin pegar", duration=1.0, success=True)
        controller.on_transcription_finished(result)

        mock_clipboard.copy.assert_called_once_with("Texto copiado sin pegar")
        mock_paster.paste_clipboard.assert_not_called()
        assert AppState.PASTING not in state_changes
        assert controller.state == AppState.DONE

    def test_transcription_finished_empty_text_returns_to_idle(self, controller, mock_clipboard, mock_paster):
        controller._state = AppState.TRANSCRIBING

        result = TranscriptionResult(text="   ", duration=0.5, success=True)
        controller.on_transcription_finished(result)

        mock_clipboard.copy.assert_not_called()
        mock_paster.paste_clipboard.assert_not_called()
        assert controller.state == AppState.IDLE

    def test_transcription_failed_emits_error_and_returns_to_idle(self, controller):
        controller._state = AppState.TRANSCRIBING

        errors = []
        status_texts = []
        controller.session_error.connect(errors.append)
        controller.status_text_updated.connect(status_texts.append)

        controller.on_transcription_failed("CUDA out of memory")

        assert controller.state == AppState.ERROR
        assert errors == ["CUDA out of memory"]
        assert "error" in status_texts[-1].lower()


class TestDictationControllerCancellation:
    """Tests cancellation flow via cancel_dictation()."""

    def test_cancel_during_listening(self, controller, mock_recorder):
        controller.toggle_dictation()
        assert controller.state == AppState.LISTENING

        controller.cancel_dictation()

        mock_recorder.stop.assert_called_once()
        assert controller.state == AppState.IDLE

    def test_cancel_during_transcribing_aborts_worker(self, controller, mock_recorder):
        controller.toggle_dictation()
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        controller._worker = mock_worker
        controller._state = AppState.TRANSCRIBING

        controller.cancel_dictation()

        mock_worker.quit.assert_called_once()
        assert controller.state == AppState.IDLE

        # Late transcription finish should be ignored
        res = TranscriptionResult(text="Late text", duration=1.0)
        controller.on_transcription_finished(res)
        assert controller.state == AppState.IDLE

    def test_cancel_when_already_idle(self, controller, mock_recorder):
        assert controller.state == AppState.IDLE
        controller.cancel_dictation()
        assert controller.state == AppState.IDLE


class TestDictationControllerHotkeyAndSignals:
    """Tests dynamic hotkey updates, amplitude forwarding, and cleanup."""

    def test_update_hotkey_success(self, controller, mock_hotkey_manager):
        mock_hotkey_manager.update_hotkey.return_value = (True, "")
        mock_hotkey_manager.get_current_hotkey.return_value = "Ctrl+Shift+D"

        hotkey_signals = []
        controller.hotkey_updated.connect(hotkey_signals.append)

        success, msg = controller.update_hotkey("Ctrl+Shift+D")

        assert success is True
        mock_hotkey_manager.update_hotkey.assert_called_once_with("Ctrl+Shift+D")
        assert controller.current_hotkey == "Ctrl+Shift+D"
        assert hotkey_signals == ["Ctrl+Shift+D"]

    def test_update_hotkey_during_listening_updates_subtext(self, controller, mock_hotkey_manager):
        controller.toggle_dictation()
        assert controller.state == AppState.LISTENING

        mock_hotkey_manager.update_hotkey.return_value = (True, "")
        mock_hotkey_manager.get_current_hotkey.return_value = "Alt+Space"

        subtexts = []
        controller.subtext_updated.connect(subtexts.append)

        controller.update_hotkey("Alt+Space")
        assert "Alt+Space para finalizar" in subtexts[-1]

    def test_restore_default_hotkey(self, controller, mock_hotkey_manager):
        mock_hotkey_manager.update_hotkey.return_value = (True, "")
        mock_hotkey_manager.get_current_hotkey.return_value = DEFAULT_HOTKEY

        success, msg = controller.restore_default_hotkey()

        assert success is True
        mock_hotkey_manager.update_hotkey.assert_called_once_with(DEFAULT_HOTKEY)

    def test_amplitude_updated_forwarding(self, controller):
        amplitudes = []
        controller.amplitude_updated.connect(amplitudes.append)

        controller._on_amplitude_updated(0.85)
        assert amplitudes == [0.85]

    def test_return_to_idle_resets_status_and_amplitude(self, controller):
        controller._state = AppState.DONE
        status_texts = []
        amplitudes = []
        controller.status_text_updated.connect(status_texts.append)
        controller.amplitude_updated.connect(amplitudes.append)

        controller._return_to_idle()

        assert controller.state == AppState.IDLE
        assert amplitudes[-1] == 0.0
        assert "Listo" in status_texts[-1]

    def test_cleanup(self, controller, mock_recorder, mock_hotkey_manager):
        controller.cleanup()
        mock_recorder.cleanup.assert_called_once()
        mock_hotkey_manager.cleanup.assert_called_once()

    def test_hotkey_triggered_signal_calls_toggle_dictation(
        self, qapp, mock_config, mock_recorder, mock_clipboard, mock_paster
    ):
        from PySide6.QtCore import QObject, Signal

        class DummyHotkeyManager(QObject):
            hotkey_triggered = Signal()

            def get_current_hotkey(self):
                return "Ctrl+Space"

            def update_hotkey(self, hk):
                return True, ""

            def cleanup(self):
                pass

        dummy_hm = DummyHotkeyManager()
        ctrl = DictationController(
            config_manager=mock_config,
            hotkey_manager=dummy_hm,
            audio_recorder=mock_recorder,
            clipboard=mock_clipboard,
            paster=mock_paster,
        )
        assert ctrl.state == AppState.IDLE
        dummy_hm.hotkey_triggered.emit()
        assert ctrl.state == AppState.LISTENING


    def test_recording_error_emits_session_error(self, controller):
        errors = []
        controller.session_error.connect(errors.append)
        controller._on_recording_error("Dispositivo desconectado")

        assert controller.state == AppState.ERROR
        assert errors == ["Dispositivo desconectado"]

    def test_spawn_worker_wires_signals(self, controller):
        audio = np.zeros(16000, dtype=np.float32)
        with patch("controllers.dictation_controller.TranscriptionWorker") as MockWorker:
            mock_instance = MagicMock()
            MockWorker.return_value = mock_instance

            controller._spawn_worker(audio)

            MockWorker.assert_called_once_with(
                audio_data=audio,
                model_name="base",
                language="es",
                model_manager=None,
                transcriber=None,
                parent=controller,
            )
            mock_instance.status_changed.connect.assert_called_once()
            mock_instance.finished.connect.assert_called_once()
            mock_instance.failed.connect.assert_called_once()
            mock_instance.start.assert_called_once()
            assert controller._worker == mock_instance

    def test_worker_status_changed_updates_status_text(self, controller):
        controller._state = AppState.TRANSCRIBING
        status_texts = []
        controller.status_text_updated.connect(status_texts.append)

        controller._on_worker_status_changed("Descargando modelo...")
        assert status_texts == ["Descargando modelo..."]

    def test_worker_status_changed_ignored_if_not_transcribing(self, controller):
        controller._state = AppState.IDLE
        status_texts = []
        controller.status_text_updated.connect(status_texts.append)

        controller._on_worker_status_changed("Descargando modelo...")
        assert len(status_texts) == 0


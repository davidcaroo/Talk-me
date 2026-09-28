from pathlib import Path
import pytest
from unittest.mock import patch

from speech.model_manager import ModelManager


def test_is_model_cached_rejects_empty_snapshot_folder(tmp_path):
    manager = ModelManager(models_dir=tmp_path)
    snapshot_dir = tmp_path / "models--Systran--faster-whisper-base" / "snapshots" / "abc123"
    snapshot_dir.mkdir(parents=True)

    with patch("faster_whisper.download_model", return_value=str(snapshot_dir)):
        assert not manager.is_model_cached("base")


def test_is_model_cached_accepts_valid_model_bin_in_snapshot(tmp_path):
    manager = ModelManager(models_dir=tmp_path)
    snapshot_dir = tmp_path / "models--Systran--faster-whisper-base" / "snapshots" / "abc123"
    snapshot_dir.mkdir(parents=True)
    model_bin = snapshot_dir / "model.bin"
    # Create file with non-zero size
    model_bin.write_bytes(b"x" * 2048)

    with patch("faster_whisper.download_model", return_value=str(snapshot_dir)):
        assert manager.is_model_cached("base")


def test_clean_stale_locks_removes_orphaned_lock_and_incomplete(tmp_path):
    manager = ModelManager(models_dir=tmp_path)
    locks_dir = tmp_path / ".locks" / "models--Systran--faster-whisper-base"
    locks_dir.mkdir(parents=True)
    stale_lock = locks_dir / "test.lock"
    stale_lock.write_text("")

    blobs_dir = tmp_path / "models--Systran--faster-whisper-base" / "blobs"
    blobs_dir.mkdir(parents=True)
    incomplete_file = blobs_dir / "test.incomplete"
    incomplete_file.write_text("")

    cleaned = manager.clean_stale_locks()
    assert cleaned >= 2
    assert not stale_lock.exists()
    assert not incomplete_file.exists()

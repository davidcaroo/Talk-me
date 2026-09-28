"""Model manager for faster-whisper local models with lazy caching."""

import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from utils.paths import get_models_dir
from utils.logger import get_logger

logger = get_logger("speech.model_manager")


class ModelManager:
    """Manages downloading, caching verification, and lazy loading of Whisper models."""

    _loaded_models: Dict[Tuple[str, str, str, int], Any] = {}

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = Path(models_dir) if models_dir is not None else get_models_dir()
        self.models_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the in-memory loaded models cache."""
        cls._loaded_models.clear()

    def clean_stale_locks(self) -> int:
        """Removes orphaned .lock and .incomplete files from interrupted downloads.

        Returns:
            Number of removed files.
        """
        removed_count = 0
        try:
            # 1. Purge .locks directory files
            locks_dir = self.models_dir / ".locks"
            if locks_dir.exists():
                for lock_file in locks_dir.rglob("*.lock"):
                    try:
                        lock_file.unlink(missing_ok=True)
                        removed_count += 1
                    except Exception as e:
                        logger.debug(f"Could not remove lock file {lock_file}: {e}")

            # 2. Purge .incomplete blob files
            for incomplete_file in self.models_dir.rglob("*.incomplete"):
                try:
                    incomplete_file.unlink(missing_ok=True)
                    removed_count += 1
                except Exception as e:
                    logger.debug(f"Could not remove incomplete file {incomplete_file}: {e}")

            if removed_count > 0:
                logger.info(f"Limpieza de caché: eliminados {removed_count} archivos residuales/bloqueos.")
        except Exception as e:
            logger.warning(f"Error limpiando bloqueos de modelos: {e}")
        return removed_count

    def is_model_cached(self, model_name: str = "base") -> bool:
        """Verifies if the model files are already downloaded locally.

        Requires that 'model.bin' exists and has valid non-zero content.

        Args:
            model_name: Name of the whisper model (e.g. 'tiny', 'base', 'small').

        Returns:
            True if model files exist locally in cache, False otherwise.
        """
        # 1. Direct path check (e.g. models_dir / "base" / "model.bin")
        direct_path = self.models_dir / model_name
        direct_bin = direct_path / "model.bin"
        if direct_path.is_dir() and direct_bin.exists():
            try:
                if direct_bin.stat().st_size > 0:
                    return True
            except OSError:
                pass

        # 2. Faster-whisper snapshot cache check via local_files_only
        try:
            from faster_whisper import download_model

            cached_path = download_model(
                model_name,
                local_files_only=True,
                cache_dir=str(self.models_dir),
            )
            if cached_path is not None:
                model_bin = Path(cached_path) / "model.bin"
                if model_bin.exists():
                    try:
                        if model_bin.stat().st_size > 0:
                            return True
                    except OSError:
                        return True
            return False
        except Exception:
            return False

    def load_model(
        self,
        model_name: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4,
    ) -> Any:
        """Lazily loads a WhisperModel into memory or returns the cached instance.

        Optimized by default for fast, lightweight local CPU execution:
        device='cpu', compute_type='int8', cpu_threads=4.

        Args:
            model_name: Model identifier (e.g. 'base', 'tiny').
            device: Compute device ('cpu', 'cuda', 'auto').
            compute_type: Quantization precision ('int8', 'float16', 'float32').
            cpu_threads: Number of CPU threads for inference.

        Returns:
            The loaded WhisperModel instance.
        """
        cache_key = (model_name, device, compute_type, cpu_threads)
        if cache_key in self._loaded_models:
            logger.debug(f"Modelo '{model_name}' recuperado desde la caché en memoria.")
            return self._loaded_models[cache_key]

        from faster_whisper import WhisperModel

        logger.info(
            f"Inicializando modelo Whisper '{model_name}' "
            f"(device={device}, compute_type={compute_type}, cpu_threads={cpu_threads})..."
        )
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
            download_root=str(self.models_dir),
        )
        self._loaded_models[cache_key] = model
        logger.info(f"Modelo Whisper '{model_name}' cargado exitosamente.")
        return model

    def preload_model_async(
        self,
        model_name: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4,
    ) -> threading.Thread:
        """Asynchronously pre-warms a cached Whisper model in background RAM.

        Runs on a daemon thread to avoid blocking application startup or GUI events.

        Returns:
            The started Thread instance.
        """
        def _warmup_target():
            try:
                self.clean_stale_locks()
                if self.is_model_cached(model_name):
                    logger.info(f"Iniciando precalentamiento de modelo Whisper '{model_name}' en RAM...")
                    self.load_model(
                        model_name=model_name,
                        device=device,
                        compute_type=compute_type,
                        cpu_threads=cpu_threads,
                    )
                    logger.info(f"Precalentamiento exitoso: modelo '{model_name}' listo en memoria.")
                else:
                    logger.info(f"Precalentamiento omitido: modelo '{model_name}' no se encuentra aún en caché.")
            except Exception as e:
                logger.warning(f"Error durante el precalentamiento del modelo '{model_name}': {e}")

        warmup_thread = threading.Thread(target=_warmup_target, daemon=True, name="ModelWarmupThread")
        warmup_thread.start()
        return warmup_thread


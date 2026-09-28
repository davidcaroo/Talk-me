"""Model manager for faster-whisper local models with lazy caching."""

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

    def is_model_cached(self, model_name: str = "base") -> bool:
        """Verifies if the model files are already downloaded locally.

        Args:
            model_name: Name of the whisper model (e.g. 'tiny', 'base', 'small').

        Returns:
            True if model files exist locally in cache, False otherwise.
        """
        # 1. Direct path check (e.g. models_dir / "base" / "model.bin")
        direct_path = self.models_dir / model_name
        if direct_path.is_dir() and (direct_path / "model.bin").exists():
            return True

        # 2. Faster-whisper snapshot cache check via local_files_only
        try:
            from faster_whisper import download_model

            cached_path = download_model(
                model_name,
                local_files_only=True,
                cache_dir=str(self.models_dir),
            )
            return cached_path is not None and Path(cached_path).exists()
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

"""Audio device enumeration and helper utilities."""

import logging
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioDevices:
    """Manages audio input device enumeration and selection."""

    @classmethod
    def get_input_devices(cls) -> list[dict]:
        """Return list of available input audio devices.

        Each dict contains:
            index (int): Device index in sounddevice.
            name (str): Device name.
            channels (int): Number of input channels.
            default_samplerate (float): Default sample rate in Hz.
            is_default (bool): True if this is the system default input device.
        """
        try:
            devices = sd.query_devices()
            default_input_idx = None
            if hasattr(sd, "default") and sd.default.device is not None:
                try:
                    default_input_idx = sd.default.device[0]
                except (TypeError, IndexError, KeyError):
                    try:
                        default_input_idx = int(sd.default.device)
                    except Exception:
                        default_input_idx = None

            input_devices = []
            for idx, dev in enumerate(devices):
                max_channels = dev.get("max_input_channels", 0)
                if max_channels > 0:
                    is_default = (idx == default_input_idx)
                    input_devices.append({
                        "index": idx,
                        "name": dev.get("name", f"Microphone {idx}"),
                        "channels": max_channels,
                        "default_samplerate": float(dev.get("default_samplerate", 16000.0)),
                        "is_default": is_default,
                    })
            return input_devices
        except Exception as e:
            logger.warning(f"Error querying audio input devices: {e}")
            return []

    @classmethod
    def get_default_input_device(cls) -> dict | None:
        """Return the system default input device dictionary or None if unavailable."""
        devices = cls.get_input_devices()
        for dev in devices:
            if dev.get("is_default"):
                return dev
        return devices[0] if devices else None

from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    duration: float
    language: str = "es"
    success: bool = True
    error: str | None = None

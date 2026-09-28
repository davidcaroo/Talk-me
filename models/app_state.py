from enum import Enum


class AppState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PAUSED = "paused"
    TRANSCRIBING = "transcribing"
    PASTING = "pasting"
    DONE = "done"
    ERROR = "error"

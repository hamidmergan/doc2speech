from .errors import (
    AudioError,
    ConfigError,
    EmptyTextError,
    LimitError,
    ModelError,
    SpeechError,
    UnsupportedFileError,
)

__version__ = "0.1.0"

__all__ = [
    "SpeechError",
    "ConfigError",
    "LimitError",
    "EmptyTextError",
    "UnsupportedFileError",
    "ModelError",
    "AudioError",
    "__version__",
]

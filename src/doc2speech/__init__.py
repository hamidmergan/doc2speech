from .chunking import split_text
from .core import preview, speak, speak_file
from .errors import (
    AudioError,
    ConfigError,
    EmptyTextError,
    LimitError,
    ModelError,
    SpeechError,
    UnsupportedFileError,
)
from .extract import extract_text
from .numbers import spell_numbers

__version__ = "0.1.0"

__all__ = [
    "speak",
    "speak_file",
    "split_text",
    "preview",
    "extract_text",
    "spell_numbers",
    "SpeechError",
    "ConfigError",
    "LimitError",
    "EmptyTextError",
    "UnsupportedFileError",
    "ModelError",
    "AudioError",
    "__version__",
]

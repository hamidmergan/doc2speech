from .audio import SUFFIXES
from .chunking import split_text
from .config import Settings, resolve
from .core import file_audio, preview, speak, speak_file
from .errors import (
    RETRY_STATUS,
    AudioError,
    ConfigError,
    EmptyTextError,
    LimitError,
    ModelError,
    SpeechError,
    UnsupportedFileError,
)
from .extract import extract_bytes, extract_text, supported_suffixes
from .numbers import spell_numbers
from .preview import preview_text

__version__ = "0.1.0"

__all__ = [
    "speak",
    "speak_file",
    "split_text",
    "preview",
    "extract_text",
    "spell_numbers",
    # helpers other tools build on
    "file_audio",
    "extract_bytes",
    "supported_suffixes",
    "preview_text",
    "Settings",
    "resolve",
    "SUFFIXES",
    "SpeechError",
    "ConfigError",
    "LimitError",
    "EmptyTextError",
    "UnsupportedFileError",
    "ModelError",
    "AudioError",
    "RETRY_STATUS",
    "__version__",
]

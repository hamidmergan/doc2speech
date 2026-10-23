class SpeechError(Exception):
    """Base class of all errors in this package."""


class ConfigError(SpeechError):
    """A setting is missing or a value is invalid."""


class LimitError(SpeechError):
    """A limit was exceeded."""


class EmptyTextError(SpeechError):
    """There is no text to read aloud."""


class UnsupportedFileError(SpeechError):
    """The file type is not supported or the file cannot be read."""


class ModelError(SpeechError):
    """The speech server did not answer, or the answer was unusable."""


class AudioError(SpeechError):
    """ffmpeg is missing, the parts could not be joined, or the audio could not be written."""

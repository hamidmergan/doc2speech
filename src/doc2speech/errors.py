"""The errors this package raises."""

# 408 Request Timeout and 429 Too Many Requests are worth a second try,
# like every 5xx. Every other 4xx stays broken until the request changes.
RETRY_STATUS = frozenset({408, 429})


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
    """The speech server did not answer, or the answer was unusable.

    ``status`` carries the HTTP status code of the answer as an ``int`` when one
    is known, and stays ``None`` when the request never reached an answer, for
    example on a timeout or a refused connection. The message text is the same
    either way.
    """

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status

    @property
    def transient(self) -> bool:
        """Whether sending the same request again can still succeed.

        A timeout or a connection failure carries no status and counts as
        transient, and so do 408, 429 and every 5xx. Every other answer is
        final, the request itself has to change before it can work.
        """
        if self.status is None:
            return True
        return self.status in RETRY_STATUS or 500 <= self.status <= 599


class AudioError(SpeechError):
    """ffmpeg is missing, the parts could not be joined, or the audio could not be written."""

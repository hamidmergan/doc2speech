"""Call an OpenAI-compatible speech endpoint (POST /audio/speech)."""

from .config import Settings
from .errors import ModelError
from .numbers import spell_numbers


def status_of(answer) -> "int | None":
    """The HTTP status code of a client error or of a response, if it has one.

    The code is read off the object the openai client hands over, never parsed
    out of a message text.
    """
    for holder in (answer, getattr(answer, "response", None)):
        status = getattr(holder, "status_code", None)
        if isinstance(status, int):
            return status
    return None


def normalize_base_url(url: str) -> str:
    """Accept a server URL with or without the /v1 suffix.

    Both http://host:8880 and http://host:8880/v1 end up calling
    http://host:8880/v1/audio/speech.
    """
    cleaned = (url or "").rstrip("/")
    if cleaned.endswith("/v1"):
        cleaned = cleaned[: -len("/v1")]
    return cleaned + "/v1"


def make_client(settings: Settings):
    from openai import OpenAI

    return OpenAI(
        base_url=normalize_base_url(settings.base_url),
        api_key=settings.api_key,
        timeout=settings.timeout,
        max_retries=settings.max_retries,
    )


def prepare_text(text: str, language: str = "") -> str:
    """One line per request, digits spelled out where the language is known."""
    text = " ".join(line.strip() for line in text.splitlines() if line.strip())
    # Digits would otherwise sound wrong, the voice guesses its language from the text.
    return spell_numbers(text, language)


def synthesize_chunk(client, settings: Settings, text: str) -> bytes:
    """Voice one part and return the audio bytes in settings.format."""
    payload = {
        "model": settings.model,
        "voice": settings.voice,
        "input": prepare_text(text, settings.language),
        "response_format": settings.format,
    }
    # Speed only goes out when it is set. Some servers slow a voice down
    # in a way that sounds like an echo.
    if settings.speed is not None:
        payload["speed"] = settings.speed
    try:
        response = client.audio.speech.create(**payload)
    except Exception as exc:
        raise ModelError(
            f"Request to {settings.base_url} failed: {exc}", status=status_of(exc)
        )
    try:
        audio = response.content
    except AttributeError:
        raise ModelError(
            "The server response has an unexpected format.", status=status_of(response)
        )
    if not audio:
        raise ModelError("The server returned no audio.", status=status_of(response))
    return audio

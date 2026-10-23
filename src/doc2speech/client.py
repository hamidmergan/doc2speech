"""Call an OpenAI-compatible speech endpoint (POST /audio/speech)."""

from .config import Settings
from .errors import ModelError
from .numbers import spell_numbers


def make_client(settings: Settings):
    from openai import OpenAI

    return OpenAI(
        base_url=settings.base_url,
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
        raise ModelError(f"Request to {settings.base_url} failed: {exc}")
    try:
        audio = response.content
    except AttributeError:
        raise ModelError("The server response has an unexpected format.")
    if not audio:
        raise ModelError("The server returned no audio.")
    return audio

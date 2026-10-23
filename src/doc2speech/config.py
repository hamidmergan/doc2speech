"""Default values and resolution of settings.

Order: argument, then environment variable, then default.
"""

import os
from dataclasses import dataclass
from typing import Optional

from .errors import ConfigError

# Characters per speech request. Many servers give up on a request after about
# 60 seconds of audio, so long texts go out in short parts.
MAX_CHARS_PER_CHUNK = 400

# Longest text that is accepted at all.
MAX_CHARS = 100_000

# Requests to the speech server at the same time. More than 4 made a busy
# server drop requests in measurements.
CONCURRENCY = 4

# Seconds per request.
TIMEOUT_SECONDS = 90
MAX_RETRIES = 2

FORMATS = ("mp3", "wav", "opus")
FORMAT = "mp3"

# Placeholder, because the OpenAI library requires a value.
# Local servers ignore it.
PLACEHOLDER_API_KEY = "none"

ENV_PREFIX = "DOC2SPEECH_"


@dataclass(frozen=True)
class Settings:
    base_url: str
    model: str
    api_key: str
    voice: str
    speed: Optional[float]
    format: str
    language: str
    max_chars_per_chunk: int
    max_chars: int
    concurrency: int
    timeout: float
    max_retries: int


def _env(name: str) -> Optional[str]:
    value = os.environ.get(ENV_PREFIX + name)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _pick(arg, env_name: str, default, cast):
    if arg is not None:
        return arg
    raw = _env(env_name)
    if raw is None:
        return default
    try:
        return cast(raw)
    except ValueError:
        raise ConfigError(
            f"Environment variable {ENV_PREFIX}{env_name} has an invalid value: {raw!r}"
        )


def resolve(
    *,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    voice: Optional[str] = None,
    speed: Optional[float] = None,
    format: Optional[str] = None,
    language: Optional[str] = None,
    max_chars_per_chunk: Optional[int] = None,
    max_chars: Optional[int] = None,
    concurrency: Optional[int] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> Settings:
    base_url = _pick(base_url, "BASE_URL", None, str)
    model = _pick(model, "MODEL", None, str)
    voice = _pick(voice, "VOICE", None, str)
    missing = []
    if not base_url:
        missing.append("base_url (--base-url or DOC2SPEECH_BASE_URL)")
    if not model:
        missing.append("model (--model or DOC2SPEECH_MODEL)")
    if not voice or not str(voice).strip():
        missing.append("voice (--voice or DOC2SPEECH_VOICE)")
    if missing:
        raise ConfigError(
            "Missing: " + ", ".join(missing) + ". "
            "Example for a local server: base_url http://localhost:11434/v1, "
            "a text-to-speech model and one of its voices."
        )

    key = _pick(api_key, "API_KEY", None, str)
    if not key:
        key = os.environ.get("OPENAI_API_KEY") or PLACEHOLDER_API_KEY

    settings = Settings(
        base_url=base_url,
        model=model,
        api_key=key,
        voice=str(voice).strip(),
        speed=_pick(speed, "SPEED", None, float),
        format=str(_pick(format, "FORMAT", FORMAT, str)).lower(),
        language=_pick(language, "LANGUAGE", "", str),
        max_chars_per_chunk=_pick(
            max_chars_per_chunk, "MAX_CHARS_PER_CHUNK", MAX_CHARS_PER_CHUNK, int
        ),
        max_chars=_pick(max_chars, "MAX_CHARS", MAX_CHARS, int),
        concurrency=_pick(concurrency, "CONCURRENCY", CONCURRENCY, int),
        timeout=_pick(timeout, "TIMEOUT", TIMEOUT_SECONDS, float),
        max_retries=_pick(max_retries, "MAX_RETRIES", MAX_RETRIES, int),
    )
    _validate(settings)
    return settings


def _validate(s: Settings) -> None:
    if s.format not in FORMATS:
        raise ConfigError(f"format must be one of {', '.join(FORMATS)}, but is {s.format!r}.")
    positive = {
        "max_chars_per_chunk": s.max_chars_per_chunk,
        "max_chars": s.max_chars,
        "concurrency": s.concurrency,
        "timeout": s.timeout,
    }
    if s.speed is not None:
        positive["speed"] = s.speed
    for name, value in positive.items():
        if value <= 0:
            raise ConfigError(f"{name} must be greater than 0, but is {value}.")
    if s.max_retries < 0:
        raise ConfigError("max_retries must not be negative.")

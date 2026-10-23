from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Lock
from typing import Callable, Optional, Union

from . import config
from .audio import SUFFIXES, ffmpeg_path, join
from .chunking import split_text
from .client import make_client, synthesize_chunk
from .errors import EmptyTextError, LimitError
from .extract import extract_text, sanitize_text
from .numbers import language_code
from .preview import preview_text

PathLike = Union[str, Path]
# Called with the number of finished parts and the total number of parts.
Progress = Callable[[int, int], None]


def _number(n: int) -> str:
    return f"{n:,}"


def _voice(text: str, settings: config.Settings, client, progress: Optional[Progress] = None) -> bytes:
    """Split, voice every part with the same voice, join in order."""
    # A part of only whitespace would be an empty request.
    chunks = [c for c in split_text(text, settings.max_chars_per_chunk) if c.strip()]
    if not chunks:
        raise EmptyTextError("Please enter some text.")
    if len(chunks) > 1:
        # Checked before the first request, so no model time is spent in vain.
        ffmpeg_path()
    client = client or make_client(settings)
    done = [0]
    lock = Lock()

    def one(chunk: str) -> bytes:
        audio = synthesize_chunk(client, settings, chunk)
        if progress is not None:
            with lock:
                done[0] += 1
                progress(done[0], len(chunks))
        return audio

    if progress is not None:
        progress(0, len(chunks))
    workers = min(settings.concurrency, len(chunks))
    if workers <= 1:
        parts = [one(chunk) for chunk in chunks]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # map returns the results in input order
            parts = list(pool.map(one, chunks))
    return join(parts, settings.format)


def speak(
    text: str,
    voice: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    *,
    client=None,
    progress: Optional[Progress] = None,
    **settings,
) -> bytes:
    """Read text aloud and return the audio bytes (mp3 unless format is set).

    Errors are raised as exceptions (subclasses of SpeechError).
    Further settings (speed, format, language, max_chars_per_chunk,
    concurrency, timeout, and so on) can be passed as keyword arguments.
    `progress` is called with the finished and the total number of parts.
    """
    resolved = config.resolve(
        voice=voice, base_url=base_url, model=model, api_key=api_key, **settings
    )
    cleaned = sanitize_text(text or "")
    if not cleaned:
        raise EmptyTextError("Please enter some text.")
    if len(cleaned) > resolved.max_chars:
        raise LimitError(
            f"Text too long ({_number(len(cleaned))} characters). "
            f"Please shorten (max {_number(resolved.max_chars)} characters)."
        )
    return _voice(cleaned, resolved, client, progress)


def speak_file(
    path: PathLike,
    output: Optional[PathLike] = None,
    voice: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    *,
    client=None,
    progress: Optional[Progress] = None,
    **settings,
) -> Path:
    """Read a text file aloud and write the audio to output.

    Without output the audio goes next to the input, with the format's
    extension (notes.md becomes notes.mp3). Returns the written path.
    """
    resolved = config.resolve(
        voice=voice, base_url=base_url, model=model, api_key=api_key, **settings
    )
    path = Path(path)
    audio = file_audio(path, resolved, client, progress)
    target = Path(output) if output is not None else path.with_suffix(SUFFIXES[resolved.format])
    target.write_bytes(audio)
    return target


def file_audio(path: Path, settings: config.Settings, client=None,
               progress: Optional[Progress] = None) -> bytes:
    """Extract, check and voice the text of a file."""
    text = extract_text(path)
    if not text.strip():
        raise EmptyTextError(f"No text found in {path.name}.")
    if len(text) > settings.max_chars:
        raise LimitError(
            f"Document too long ({_number(len(text))} characters). "
            f"Please split (max {_number(settings.max_chars)} characters)."
        )
    return _voice(text, settings, client, progress)


def preview(
    voice: Optional[str] = None,
    language: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    *,
    client=None,
    **settings,
) -> bytes:
    """Let a voice speak a short example sentence (English or German).

    Any language other than English gets the German sentence. The sentence
    is spoken at normal speed.
    """
    resolved = config.resolve(
        voice=voice, base_url=base_url, model=model, api_key=api_key,
        language=language, **settings
    )
    text = preview_text(language_code(resolved.language) or "de")
    resolved = replace(resolved, speed=None, language="")
    client = client or make_client(resolved)
    return synthesize_chunk(client, resolved, text)



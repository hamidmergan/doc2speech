"""ffmpeg is a system requirement, it joins the audio parts losslessly."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from .errors import AudioError

# File extension per response format, ffmpeg picks the muxer from it.
SUFFIXES = {"mp3": ".mp3", "wav": ".wav", "opus": ".opus"}


def ffmpeg_path() -> str:
    """The ffmpeg binary on PATH, or an AudioError that says how to fix it."""
    path = shutil.which("ffmpeg")
    if path is None:
        raise AudioError(
            "ffmpeg was not found on PATH. It is needed to join the audio parts. "
            "Install it, for example with 'apt install ffmpeg' or 'brew install ffmpeg'."
        )
    return path


def join(parts: List[bytes], format: str) -> bytes:
    """Join audio parts of the same format without re-encoding (concat demuxer)."""
    if not parts:
        raise AudioError("There are no audio parts to join.")
    if len(parts) == 1:
        return parts[0]
    ffmpeg = ffmpeg_path()
    suffix = SUFFIXES[format]
    with tempfile.TemporaryDirectory(prefix="doc2speech_") as tmp:
        folder = Path(tmp)
        lines = []
        for index, data in enumerate(parts):
            name = f"part_{index:03d}{suffix}"
            (folder / name).write_bytes(data)
            lines.append(f"file '{name}'")
        listing = folder / "parts.txt"
        listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
        target = folder / f"joined{suffix}"
        result = subprocess.run(
            [ffmpeg, "-v", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", str(target)],
            capture_output=True,
            timeout=600,
        )
        if result.returncode != 0 or not target.is_file():
            err = result.stderr.decode("utf-8", "replace")[-300:]
            raise AudioError(f"ffmpeg could not join the audio parts: {err}")
        return target.read_bytes()

"""ffmpeg is a system requirement, it joins the audio parts losslessly."""

import shutil

from .errors import AudioError


def ffmpeg_path() -> str:
    """The ffmpeg binary on PATH, or an AudioError that says how to fix it."""
    path = shutil.which("ffmpeg")
    if path is None:
        raise AudioError(
            "ffmpeg was not found on PATH. It is needed to join the audio parts. "
            "Install it, for example with 'apt install ffmpeg' or 'brew install ffmpeg'."
        )
    return path

"""Web API for the speech page.

One job at a time: send text or a file, follow the progress, play and
download the result. Nothing is stored on disk, the audio lives in memory
until the next job replaces it.
"""

import threading
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import config
from ..audio import SUFFIXES
from ..core import preview as preview_audio
from ..core import speak
from ..errors import ConfigError, SpeechError
from ..extract import extract_bytes, supported_suffixes

STATIC = Path(__file__).parent / "static"
MB = 1024 * 1024

# Largest upload the page accepts. A text file of that size is far longer
# than max_chars anyway, the check just keeps the memory bounded.
MAX_UPLOAD_MB = 25

MEDIA_TYPES = {"mp3": "audio/mpeg", "wav": "audio/wav", "opus": "audio/ogg"}


class Job:
    """The one job the page is working on, plus its finished audio."""

    def __init__(self) -> None:
        self.state = "idle"  # idle, running, done or error
        self.done = 0
        self.total = 0
        self.error = ""
        self.name = "text"
        self.format = "mp3"
        self.audio = b""

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "done": self.done,
            "total": self.total,
            "error": self.error,
            "name": self.filename if self.state == "done" else "",
        }

    @property
    def filename(self) -> str:
        return self.name + SUFFIXES.get(self.format, ".mp3")


def _hostname(host: str) -> str:
    if host.startswith("["):
        return host[1:host.find("]")].lower()
    return host.rsplit(":", 1)[0].lower() if host.count(":") == 1 else host.lower()


def _stem(filename: str) -> str:
    """A safe file name stem for the download, from the uploaded name."""
    stem = Path(filename.replace("\\", "/")).stem
    cleaned = "".join(ch for ch in stem if ch.isalnum() or ch in " -_.").strip()
    return cleaned[:80] or "text"


def create_app(settings: Optional[config.Settings] = None,
               allowed_hosts: Optional[Sequence[str]] = None,
               client=None) -> FastAPI:
    """The speech page and its JSON API.

    `settings` are the defaults of the page. Base URL, model, voice and the
    rest can also be typed into the fields of the page. `allowed_hosts` limits
    the Host header (against DNS rebinding), requests from another origin are
    refused.
    """
    job = Job()
    lock = threading.Lock()

    app = FastAPI(title="doc2speech")
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    hosts = {h.lower() for h in allowed_hosts} if allowed_hosts is not None else None

    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = request.headers.get("host", "")
        if hosts is not None and _hostname(host) not in hosts:
            return PlainTextResponse("Unknown host", status_code=400)
        origin = request.headers.get("origin")
        own = {host.lower(), request.headers.get("x-forwarded-host", "").lower()}  # also behind a reverse proxy
        if origin is not None and urlsplit(origin).netloc.lower() not in own:
            return PlainTextResponse("Cross-origin requests are not allowed", status_code=403)
        if request.url.path in ("/api/speak", "/api/preview"):
            # refuse a too large upload before it is read, one MB of room for the form around the file
            length = request.headers.get("content-length", "")
            if length.isdigit() and int(length) > MAX_UPLOAD_MB * MB + MB:
                return PlainTextResponse(
                    f"The upload is larger than {MAX_UPLOAD_MB} MB.", status_code=413)
        return await call_next(request)

    def options(voice: str, speed: str, format: str, language: str,
                base_url: str, model: str, api_key: str) -> dict:
        """The settings of one request: what the page sends, then the defaults."""
        chosen = {
            "voice": voice.strip() or None,
            "format": format.strip() or None,
            "language": language.strip() or None,
            "base_url": base_url.strip() or None,
            "model": model.strip() or None,
            "api_key": api_key.strip() or None,
        }
        if settings is not None:
            fallback = {
                "voice": settings.voice,
                "format": settings.format,
                "language": settings.language,
                "base_url": settings.base_url,
                "model": settings.model,
                "api_key": settings.api_key,
            }
            chosen = {k: v if v is not None else fallback[k] or None for k, v in chosen.items()}
        try:
            chosen["speed"] = float(speed) if speed.strip() else None
        except ValueError:
            raise HTTPException(400, "Speed must be a number, for example 1.1.")
        if chosen["speed"] is None and settings is not None:
            chosen["speed"] = settings.speed
        return chosen

    def run(text: str, chosen: dict) -> None:
        def report(done: int, total: int) -> None:
            with lock:
                job.done, job.total = done, total

        try:
            audio = speak(text, client=client, progress=report, **chosen)
        except SpeechError as exc:
            with lock:
                job.state, job.error = "error", str(exc)
            return
        with lock:
            job.state, job.audio, job.error = "done", audio, ""

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/info")
    def info():
        """What the page fills into its fields, and what it tells the user."""
        return {
            "base_url": settings.base_url if settings else "",
            "model": settings.model if settings else "",
            "voice": settings.voice if settings else "",
            "language": settings.language if settings else "",
            "format": settings.format if settings else config.FORMAT,
            "speed": settings.speed if settings else None,
            "has_key": bool(settings and settings.api_key != config.PLACEHOLDER_API_KEY),
            "formats": list(config.FORMATS),
            "max_chars": settings.max_chars if settings else config.MAX_CHARS,
            "max_upload_mb": MAX_UPLOAD_MB,
            "extensions": supported_suffixes(),
        }

    @app.post("/api/speak")
    async def start(
        text: str = Form(""),
        voice: str = Form(""),
        speed: str = Form(""),
        format: str = Form(""),
        language: str = Form(""),
        base_url: str = Form(""),
        model: str = Form(""),
        api_key: str = Form(""),
        file: Optional[UploadFile] = File(None),
    ):
        chosen = options(voice, speed, format, language, base_url, model, api_key)
        name = "text"
        if file is not None and file.filename:
            data = await file.read()
            if len(data) > MAX_UPLOAD_MB * MB:
                raise HTTPException(413, f"The file is larger than {MAX_UPLOAD_MB} MB.")
            try:
                text = extract_bytes(file.filename, data)
            except SpeechError as exc:
                raise HTTPException(400, str(exc))
            if not text.strip():
                raise HTTPException(400, f"No text found in {Path(file.filename).name}.")
            name = _stem(file.filename)
        if not text.strip():
            raise HTTPException(400, "Please enter some text.")
        try:
            resolved = config.resolve(**chosen)
        except ConfigError as exc:
            raise HTTPException(400, str(exc))
        if len(text) > resolved.max_chars:
            raise HTTPException(
                400,
                f"Text too long ({len(text):,} characters). "
                f"Please shorten (max {resolved.max_chars:,} characters).",
            )
        with lock:
            if job.state == "running":
                raise HTTPException(409, "A text is already being read aloud.")
            job.state, job.done, job.total, job.error = "running", 0, 0, ""
            job.audio, job.name, job.format = b"", name, resolved.format
        threading.Thread(target=run, args=(text, chosen), daemon=True).start()
        return {"state": "running"}

    @app.get("/api/job")
    def state():
        with lock:
            return job.as_dict()

    @app.get("/api/audio")
    def audio():
        with lock:
            if job.state != "done" or not job.audio:
                raise HTTPException(404, "There is no audio yet.")
            data, filename, fmt = job.audio, job.filename, job.format
        return Response(
            content=data,
            media_type=MEDIA_TYPES.get(fmt, "application/octet-stream"),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/api/preview")
    def voice_preview(
        voice: str = Form(""),
        language: str = Form(""),
        format: str = Form(""),
        base_url: str = Form(""),
        model: str = Form(""),
        api_key: str = Form(""),
    ):
        chosen = options(voice, "", format, language, base_url, model, api_key)
        chosen.pop("speed")
        try:
            data = preview_audio(client=client, **chosen)
        except ConfigError as exc:
            raise HTTPException(400, str(exc))
        except SpeechError as exc:
            raise HTTPException(502, str(exc))
        return Response(content=data, media_type=MEDIA_TYPES.get(chosen["format"] or "mp3", "audio/mpeg"))

    return app

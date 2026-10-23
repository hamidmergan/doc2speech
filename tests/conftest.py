import io
import json
import shutil
import subprocess
import tempfile
import threading
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def _wav(seconds=0.2, rate=16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buffer.getvalue()


def _samples() -> dict:
    """Small valid audio per format. mp3 and opus need ffmpeg to be made."""
    samples = {"wav": _wav(), "mp3": b"ID3fake-mp3", "opus": b"OggSfake-opus"}
    if HAS_FFMPEG:
        with tempfile.TemporaryDirectory() as tmp:
            for fmt in ("mp3", "opus"):
                target = Path(tmp) / f"a.{fmt}"
                subprocess.run(
                    ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                     "sine=frequency=440:duration=0.2", "-ar", "24000", "-ac", "1", str(target)],
                    check=True,
                )
                samples[fmt] = target.read_bytes()
    return samples


SAMPLES = _samples()


class FakeServer:
    """Answers POST /v1/audio/speech with small audio in the requested format."""

    def __init__(self):
        self.requests = []
        self.fail = False
        # Status code a failing request is answered with.
        self.fail_status = 500
        # Request numbers (1 for the first one) that are answered with the fail status.
        self.fail_indexes = set()
        self.lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))
                with outer.lock:
                    outer.requests.append({
                        "path": self.path,
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": body,
                    })
                    number = len(outer.requests)
                    broken = outer.fail or number in outer.fail_indexes
                    status = outer.fail_status
                if broken or not self.path.endswith("/audio/speech"):
                    data = b'{"error": {"message": "broken"}}'
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                data = SAMPLES[body.get("response_format", "mp3")]
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.httpd.server_port}/v1"

    @property
    def inputs(self):
        return [r["body"]["input"] for r in self.requests]

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    s = FakeServer()
    yield s
    s.stop()


@pytest.fixture
def conf(server):
    """The three required settings for the fake server."""
    return {"base_url": server.base_url, "model": "tts-model", "voice": "alloy", "max_retries": 0}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    import os

    for name in list(os.environ):
        if name.startswith("DOC2SPEECH_") or name == "OPENAI_API_KEY":
            monkeypatch.delenv(name)


@pytest.fixture
def no_ffmpeg(monkeypatch):
    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda name, *a, **k: None if name == "ffmpeg" else real(name, *a, **k))


needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg is not installed")


def make_pdf(path: Path, lines) -> Path:
    """A minimal PDF with a text layer, one line per entry."""
    text_ops = "BT /F1 12 Tf 72 720 Td " + " ".join(
        f"({line}) Tj 0 -16 Td" for line in lines
    ) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(text_ops)} >>\nstream\n{text_ops}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(out)
    return path


def make_docx(path: Path, paragraphs) -> Path:
    from docx import Document

    doc = Document()
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    doc.save(str(path))
    return path

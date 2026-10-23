"""The web page and its JSON API, against the fake speech server."""

import threading
import time

import pytest
from conftest import SAMPLES, make_docx

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from doc2speech.config import resolve  # noqa: E402
from doc2speech.web.app import create_app  # noqa: E402


@pytest.fixture
def client(server):
    settings = resolve(base_url=server.base_url, model="tts-model", voice="alloy", max_retries=0)
    with TestClient(create_app(settings, allowed_hosts=["testserver"])) as c:
        yield c


def finish(client, timeout=10.0):
    """Wait for the one job of the page and return its state."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get("/api/job").json()
        if job["state"] not in ("running",):
            return job
        time.sleep(0.02)
    raise AssertionError("the job did not finish")


def test_page_is_served(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Text to audio" in page.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_info_fills_the_fields(client):
    info = client.get("/api/info").json()
    assert info["model"] == "tts-model"
    assert info["voice"] == "alloy"
    assert info["format"] == "mp3"
    assert info["has_key"] is False
    assert info["formats"] == ["mp3", "wav", "opus"]
    assert ".docx" in info["extensions"] and ".pdf" in info["extensions"]


def test_text_becomes_audio(client, server):
    assert client.post("/api/speak", data={"text": "Hello from the page."}).json() == {"state": "running"}
    job = finish(client)
    assert job["state"] == "done"
    assert job["name"] == "text.mp3"
    assert server.inputs == ["Hello from the page."]
    audio = client.get("/api/audio")
    assert audio.content == SAMPLES["mp3"]
    assert audio.headers["content-type"] == "audio/mpeg"
    assert 'filename="text.mp3"' in audio.headers["content-disposition"]


def test_fields_of_the_page_win_over_the_server_settings(client, server):
    client.post("/api/speak", data={
        "text": "It was 47.", "voice": "nova", "speed": "1.2", "format": "wav", "language": "en",
    })
    assert finish(client)["state"] == "done"
    body = server.requests[0]["body"]
    assert body["voice"] == "nova"
    assert body["speed"] == 1.2
    assert body["response_format"] == "wav"
    assert body["input"] == "It was forty-seven."
    assert client.get("/api/job").json()["name"] == "text.wav"


def test_uploaded_file_is_read(client, server, tmp_path):
    source = make_docx(tmp_path / "my notes.docx", ["First paragraph.", "Second paragraph."])
    with open(source, "rb") as f:
        response = client.post("/api/speak", files={"file": ("my notes.docx", f)})
    assert response.status_code == 200
    job = finish(client)
    assert job["state"] == "done"
    assert job["name"] == "my notes.mp3"
    assert server.inputs == ["First paragraph. Second paragraph."]


def test_unsupported_upload(client):
    response = client.post("/api/speak", files={"file": ("slides.odp", b"x")})
    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]


def test_empty_text(client):
    response = client.post("/api/speak", data={"text": "   "})
    assert response.status_code == 400
    assert "Please enter some text" in response.json()["detail"]


def test_text_too_long(client):
    response = client.post("/api/speak", data={"text": "a" * 100_001})
    assert response.status_code == 400
    assert "Text too long" in response.json()["detail"]


def test_missing_configuration_is_reported(server):
    with TestClient(create_app(None, allowed_hosts=["testserver"])) as client:
        response = client.post("/api/speak", data={"text": "Hello."})
        assert response.status_code == 400
        assert "DOC2SPEECH_BASE_URL" in response.json()["detail"]


def test_a_server_error_ends_the_job(client, server):
    server.fail = True
    client.post("/api/speak", data={"text": "Hello."})
    job = finish(client)
    assert job["state"] == "error"
    assert "failed" in job["error"]
    assert client.get("/api/audio").status_code == 404


def test_a_second_text_is_refused_while_one_is_running(client, monkeypatch):
    """The page works on one job at a time."""
    gate = threading.Event()

    def wait(text, **kwargs):
        gate.wait(5)
        return SAMPLES["mp3"]

    monkeypatch.setattr("doc2speech.web.app.speak", wait)
    assert client.post("/api/speak", data={"text": "First."}).status_code == 200
    second = client.post("/api/speak", data={"text": "Second."})
    assert second.status_code == 409
    assert "already being read aloud" in second.json()["detail"]
    gate.set()
    assert finish(client)["state"] == "done"


def test_an_unexpected_error_ends_the_job_and_frees_the_page(client, monkeypatch):
    """Any error ends the job, otherwise the page stays busy until a restart."""
    def boom(text, **kwargs):
        raise RuntimeError("something unexpected")

    monkeypatch.setattr("doc2speech.web.app.speak", boom)
    client.post("/api/speak", data={"text": "Hello."})
    job = finish(client, timeout=2.0)
    assert job["state"] == "error"
    assert "something unexpected" in job["error"]
    # the page takes the next text instead of answering 409 for ever
    assert client.post("/api/speak", data={"text": "Hello again."}).status_code == 200


def test_no_audio_before_the_first_job(client):
    assert client.get("/api/audio").status_code == 404


def test_preview_speaks_the_example_sentence(client, server):
    response = client.post("/api/preview", data={"voice": "nova", "language": "en"})
    assert response.status_code == 200
    assert response.content == SAMPLES["mp3"]
    assert server.requests[0]["body"]["voice"] == "nova"
    assert server.inputs[0].startswith("Hello!")


def test_preview_reports_a_broken_server(client, server):
    server.fail = True
    response = client.post("/api/preview", data={"voice": "nova"})
    assert response.status_code == 502


def test_an_unknown_host_is_refused(client):
    assert client.get("/", headers={"host": "evil.example"}).status_code == 400


def test_another_origin_is_refused(client):
    response = client.post("/api/speak", data={"text": "Hello."},
                           headers={"origin": "http://evil.example"})
    assert response.status_code == 403


def test_an_oversized_upload_is_refused_before_it_is_read(client):
    response = client.post("/api/speak", data={"text": "Hello."},
                           headers={"content-length": str(200 * 1024 * 1024)})
    assert response.status_code == 413

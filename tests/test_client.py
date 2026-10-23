"""What goes out to the speech server, and what comes back."""

import pytest

from doc2speech import ModelError, speak


def test_request_goes_to_audio_speech(server, conf):
    speak("Hello everyone.", **conf)
    request = server.requests[0]
    assert request["path"] == "/v1/audio/speech"
    body = request["body"]
    assert body["model"] == "tts-model"
    assert body["voice"] == "alloy"
    assert body["input"] == "Hello everyone."
    assert body["response_format"] == "mp3"


@pytest.mark.parametrize("suffix", ["", "/", "/v1", "/v1/"])
def test_a_base_url_with_or_without_v1_reaches_the_endpoint(server, conf, suffix):
    """Many servers are copied from a README without the /v1 part."""
    root = conf["base_url"][: -len("/v1")]
    speak("Hello.", **{**conf, "base_url": root + suffix})
    assert server.requests[0]["path"] == "/v1/audio/speech"


def test_returns_the_audio_bytes(server, conf):
    from conftest import SAMPLES

    assert speak("Hello everyone.", **conf) == SAMPLES["mp3"]


def test_no_speed_goes_out_by_default(server, conf):
    """A voice the server slows down can echo, so no tempo is sent unless asked for."""
    speak("Hello.", **conf)
    assert "speed" not in server.requests[0]["body"]


def test_speed_goes_out_when_set(server, conf):
    speak("Hello.", speed=1.25, **conf)
    assert server.requests[0]["body"]["speed"] == 1.25


@pytest.mark.parametrize("fmt", ["mp3", "wav", "opus"])
def test_format_is_requested(server, conf, fmt):
    speak("Hello.", format=fmt, **conf)
    assert server.requests[0]["body"]["response_format"] == fmt


def test_lines_are_joined_into_one(server, conf):
    speak("First line\n\n  second line  \nthird", **conf)
    assert server.inputs == ["First line second line third"]


def test_without_key_a_placeholder_is_sent(server, conf):
    speak("Hello.", **conf)
    assert server.requests[0]["headers"]["authorization"] == "Bearer none"


def test_with_key_the_key_is_sent(server, conf):
    speak("Hello.", api_key="secret", **conf)
    assert server.requests[0]["headers"]["authorization"] == "Bearer secret"


def test_openai_api_key_is_the_fallback(server, conf, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    speak("Hello.", **conf)
    assert server.requests[0]["headers"]["authorization"] == "Bearer from-env"


def test_server_error_becomes_model_error(server, conf):
    server.fail = True
    with pytest.raises(ModelError, match="Request to"):
        speak("Hello.", **conf)


def test_unreachable_server_becomes_model_error():
    with pytest.raises(ModelError):
        speak("Hello.", base_url="http://127.0.0.1:9/v1", model="m", voice="v", max_retries=0, timeout=2)

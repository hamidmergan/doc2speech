import pytest

from doc2speech import ConfigError, speak
from doc2speech.config import resolve


def test_everything_missing_names_all_settings():
    with pytest.raises(ConfigError) as error:
        resolve()
    message = str(error.value)
    assert "--base-url" in message and "DOC2SPEECH_BASE_URL" in message
    assert "--model" in message and "DOC2SPEECH_MODEL" in message
    assert "--voice" in message and "DOC2SPEECH_VOICE" in message


@pytest.mark.parametrize("missing", ["base_url", "model", "voice"])
def test_each_setting_is_required(missing):
    values = {"base_url": "http://localhost:11434/v1", "model": "m", "voice": "v"}
    values.pop(missing)
    with pytest.raises(ConfigError, match=missing):
        resolve(**values)


def test_voice_has_no_default():
    with pytest.raises(ConfigError, match="voice"):
        resolve(base_url="http://x/v1", model="m")


def test_blank_voice_counts_as_missing():
    with pytest.raises(ConfigError, match="voice"):
        resolve(base_url="http://x/v1", model="m", voice="  ")


def test_values_from_the_environment(monkeypatch):
    monkeypatch.setenv("DOC2SPEECH_BASE_URL", "http://env/v1")
    monkeypatch.setenv("DOC2SPEECH_MODEL", "env-model")
    monkeypatch.setenv("DOC2SPEECH_VOICE", "nova")
    monkeypatch.setenv("DOC2SPEECH_API_KEY", "k")
    monkeypatch.setenv("DOC2SPEECH_FORMAT", "WAV")
    monkeypatch.setenv("DOC2SPEECH_SPEED", "0.9")
    s = resolve()
    assert (s.base_url, s.model, s.voice, s.api_key, s.format, s.speed) == (
        "http://env/v1", "env-model", "nova", "k", "wav", 0.9)


def test_argument_wins_over_environment(monkeypatch):
    monkeypatch.setenv("DOC2SPEECH_VOICE", "nova")
    s = resolve(base_url="http://x/v1", model="m", voice="alloy")
    assert s.voice == "alloy"


def test_defaults():
    s = resolve(base_url="http://x/v1", model="m", voice="v")
    assert s.api_key == "none"
    assert s.speed is None
    assert s.format == "mp3"
    assert s.language == ""
    assert s.max_chars_per_chunk == 400
    assert s.max_chars == 100_000
    assert s.concurrency == 4
    assert s.timeout == 90


def test_invalid_format():
    with pytest.raises(ConfigError, match="format"):
        resolve(base_url="http://x/v1", model="m", voice="v", format="flac")


@pytest.mark.parametrize("name", ["speed", "max_chars_per_chunk", "max_chars", "concurrency", "timeout"])
def test_values_must_be_positive(name):
    with pytest.raises(ConfigError, match=name):
        resolve(base_url="http://x/v1", model="m", voice="v", **{name: 0})


def test_invalid_environment_value(monkeypatch):
    monkeypatch.setenv("DOC2SPEECH_CONCURRENCY", "many")
    with pytest.raises(ConfigError, match="DOC2SPEECH_CONCURRENCY"):
        resolve(base_url="http://x/v1", model="m", voice="v")


def test_speak_checks_configuration_before_anything_else(server):
    with pytest.raises(ConfigError):
        speak("Hello.", base_url=server.base_url, model="m")
    assert server.requests == []

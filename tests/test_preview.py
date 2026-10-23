"""The short example sentence a voice introduces itself with."""

from doc2speech import preview
from doc2speech.preview import preview_text


def _conf(conf):
    conf = dict(conf)
    return conf.pop("voice"), conf


def test_english_gets_the_english_sentence(server, conf):
    voice, rest = _conf(conf)
    preview(voice, "en", **rest)
    assert server.inputs[0].startswith("Hello!")


def test_german_gets_the_german_sentence(server, conf):
    voice, rest = _conf(conf)
    preview(voice, "de", **rest)
    assert server.inputs[0].startswith("Hallo!")


def test_without_language_the_german_sentence(server, conf):
    voice, rest = _conf(conf)
    preview(voice, **rest)
    assert server.inputs[0].startswith("Hallo!")


def test_language_variants_count(server, conf):
    voice, rest = _conf(conf)
    preview(voice, "en-US", **rest)
    assert server.inputs[0].startswith("Hello!")


def test_other_languages_fall_back_to_german():
    assert preview_text("fr") == preview_text("de")


def test_preview_uses_the_given_voice(server, conf):
    _, rest = _conf(conf)
    preview("nova", "en", **rest)
    assert server.requests[0]["body"]["voice"] == "nova"


def test_preview_returns_the_audio(server, conf):
    from conftest import SAMPLES

    voice, rest = _conf(conf)
    assert preview(voice, "en", **rest) == SAMPLES["mp3"]

"""Numbers are only spelled out when the language is known."""

from doc2speech import preview, speak


def test_english_text_gets_spelled_out_numbers(server, conf):
    speak("The result was 47 percent.", language="EN", **conf)
    assert server.inputs == ["The result was forty-seven percent."]


def test_without_a_known_language_the_digits_stay(server, conf):
    """Guessing would be worse than digits, a wrong language sounds wrong."""
    speak("The result was 47 percent.", **conf)
    assert server.inputs == ["The result was 47 percent."]


def test_german_text_stays_as_it_is(server, conf):
    """The wrong reading is measured for English only, so only there is anything touched."""
    speak("Es waren 47 Personen.", language="DE", **conf)
    assert server.inputs == ["Es waren 47 Personen."]


def test_language_comes_from_the_environment(server, conf, monkeypatch):
    monkeypatch.setenv("DOC2SPEECH_LANGUAGE", "en-US")
    speak("published in 1986.", **conf)
    assert server.inputs == ["published in nineteen eighty-six."]


def test_text_without_digits_goes_out_unchanged(server, conf):
    speak("Hello everyone and welcome.", language="EN", **conf)
    assert server.inputs == ["Hello everyone and welcome."]


def test_every_part_is_spelled_out(server, conf, no_ffmpeg):
    """Each part follows the same rule, not only the first."""
    import pytest

    from doc2speech import AudioError

    # two parts need ffmpeg, without it the error comes before any request
    with pytest.raises(AudioError):
        speak("It was 47. " * 60, language="EN", **conf)
    assert server.requests == []


def test_preview_sends_no_speed_and_no_spelling(server, conf):
    conf = dict(conf)
    preview(conf.pop("voice"), "en", speed=0.8, **conf)
    body = server.requests[0]["body"]
    assert "speed" not in body
    assert body["input"].startswith("Hello!")

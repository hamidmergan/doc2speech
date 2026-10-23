"""What a failed request tells a caller: the status code and whether to try again."""

import pytest

from doc2speech import ModelError, speak


def _failing(server, conf, status):
    """Let the fake server answer the next request with the given status code."""
    server.fail = True
    server.fail_status = status
    with pytest.raises(ModelError) as caught:
        speak("Hello.", **conf)
    return caught.value


@pytest.mark.parametrize(
    "status, transient",
    [(503, True), (429, True), (408, True), (401, False), (400, False)],
)
def test_the_status_code_and_the_verdict_come_from_the_answer(server, conf, status, transient):
    error = _failing(server, conf, status)
    assert error.status == status
    assert error.transient is transient


def test_a_refused_connection_has_no_status_and_is_transient(conf):
    """Port 1 is closed, so the request never reaches an answer."""
    with pytest.raises(ModelError) as caught:
        speak("Hello.", **{**conf, "base_url": "http://127.0.0.1:1/v1"})
    assert caught.value.status is None
    assert caught.value.transient is True


def test_the_message_of_a_503_is_unchanged(server, conf):
    """Callers that still match on the text keep working."""
    error = _failing(server, conf, 503)
    text = str(error)
    assert text.startswith(f"Request to {conf['base_url']} failed: ")
    assert "Error code: 503" in text


def test_a_model_error_without_a_status_defaults_to_none_and_transient():
    error = ModelError("The server returned no audio.")
    assert error.status is None
    assert error.transient is True
    assert str(error) == "The server returned no audio."


def test_the_status_is_an_int_and_not_a_string(server, conf):
    assert isinstance(_failing(server, conf, 502).status, int)

"""Long texts have to be split early, many servers abort a request after 60 seconds."""

import pytest

from doc2speech import split_text
from doc2speech.config import MAX_CHARS_PER_CHUNK


def test_short_text_stays_one_request():
    assert split_text("Good morning.") == ["Good morning."]


def test_script_length_text_is_split():
    """1500 to 2000 characters is a normal script length and has to split."""
    script = "This is a sentence about academic writing and research. " * 35
    chunks = split_text(script)
    assert len(chunks) > 1
    assert all(len(c) <= MAX_CHARS_PER_CHUNK for c in chunks)


def test_the_environment_sets_the_default_limit(monkeypatch):
    """split_text and speak have to agree on the limit, both read the environment."""
    script = "This is a sentence about academic writing and research. " * 35
    monkeypatch.setenv("DOC2SPEECH_MAX_CHARS_PER_CHUNK", "150")
    chunks = split_text(script)
    assert all(len(c) <= 150 for c in chunks)
    assert len(chunks) > len(split_text(script, MAX_CHARS_PER_CHUNK))


def test_an_argument_wins_over_the_environment(monkeypatch):
    script = "This is a sentence about academic writing and research. " * 35
    monkeypatch.setenv("DOC2SPEECH_MAX_CHARS_PER_CHUNK", "150")
    chunks = split_text(script, 400)
    assert max(len(c) for c in chunks) > 150


def test_nothing_is_lost_or_duplicated():
    script = "First sentence. Second sentence! Third sentence? " * 40
    assert "".join(split_text(script)) == script


def test_splits_at_sentence_ends():
    """Splitting mid-sentence is audible in the recording."""
    script = "A complete sentence with some length to it. " * 30
    for chunk in split_text(script)[:-1]:
        assert chunk.rstrip().endswith((".", "!", "?")), f"cut inside a sentence: {chunk[-40:]!r}"


def test_splits_at_sentence_ends_with_line_breaks():
    script = "A complete sentence with some length to it.\n" * 30
    for chunk in split_text(script)[:-1]:
        assert chunk.endswith(".\n")


def test_falls_back_to_word_boundary_without_punctuation():
    """Without punctuation it still must not cut inside a word."""
    script = "word " * 300
    chunks = split_text(script)
    assert len(chunks) > 1
    for chunk in chunks[:-1]:
        assert chunk.endswith(" ") or chunk.endswith("word"), f"cut inside a word: {chunk[-12:]!r}"


def test_hard_cut_when_a_single_word_is_longer_than_the_limit():
    """A single overlong word must not trigger an endless loop."""
    chunks = split_text("A" * (MAX_CHARS_PER_CHUNK * 3))
    assert len(chunks) == 3
    assert all(len(c) <= MAX_CHARS_PER_CHUNK for c in chunks)


@pytest.mark.parametrize("limit", [120, 400, 2000])
def test_limit_is_configurable(limit):
    script = "A sentence with a period. " * 200
    chunks = split_text(script, max_chars=limit)
    assert all(len(c) <= limit for c in chunks)
    assert "".join(chunks) == script


def test_german_text_splits_the_same_way():
    script = "Ein vollständiger Satz mit etwas Länge. " * 30
    chunks = split_text(script)
    assert "".join(chunks) == script
    for chunk in chunks[:-1]:
        assert chunk.rstrip().endswith(".")

"""Split, voice and join: the whole flow from text to one audio file."""

import subprocess

import pytest
from conftest import SAMPLES, make_docx, make_pdf, needs_ffmpeg

from doc2speech import (
    AudioError,
    EmptyTextError,
    LimitError,
    UnsupportedFileError,
    extract_text,
    speak,
    speak_file,
)

LONG = "This is one sentence of a longer text. " * 40  # about 1600 characters, 4 parts


def _duration(path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def test_short_text_is_one_request_and_needs_no_ffmpeg(server, conf, no_ffmpeg):
    assert speak("Short text.", **conf) == SAMPLES["mp3"]
    assert len(server.requests) == 1


def test_long_text_without_ffmpeg_fails_before_any_request(server, conf, no_ffmpeg):
    with pytest.raises(AudioError, match="ffmpeg"):
        speak(LONG, **conf)
    assert server.requests == []


def test_parts_go_out_in_full_and_with_one_voice(server, conf, monkeypatch):
    """One output never mixes two voices, and no text is lost."""
    monkeypatch.setattr("doc2speech.core.join", lambda parts, fmt: b"".join(parts))
    monkeypatch.setattr("doc2speech.core.ffmpeg_path", lambda: "ffmpeg")
    speak(LONG, **conf)
    assert len(server.requests) == 4
    assert {r["body"]["voice"] for r in server.requests} == {"alloy"}
    assert {r["body"]["model"] for r in server.requests} == {"tts-model"}
    assert sorted(server.inputs) == sorted(c.strip() for c in __import__("doc2speech").split_text(LONG))


def test_parts_are_joined_in_text_order(server, conf, monkeypatch):
    """Requests run in parallel, the result keeps the order of the text."""
    seen = {}

    def fake_join(parts, fmt):
        seen["parts"] = parts
        return b"joined"

    monkeypatch.setattr("doc2speech.core.join", fake_join)
    monkeypatch.setattr("doc2speech.core.ffmpeg_path", lambda: "ffmpeg")
    monkeypatch.setattr(
        "doc2speech.core.synthesize_chunk",
        lambda client, settings, text: text.encode(),
    )
    text = " ".join(f"Sentence number {i} is here." for i in range(60))
    assert speak(text, concurrency=4, **conf) == b"joined"
    assert b"".join(seen["parts"]).decode() == text


@needs_ffmpeg
@pytest.mark.parametrize("fmt", ["mp3", "wav", "opus"])
def test_parts_are_joined_with_ffmpeg(server, conf, tmp_path, fmt):
    """Four parts give one file of four times the length, nothing is dropped."""
    one = tmp_path / f"one.{fmt}"
    one.write_bytes(SAMPLES[fmt])
    audio = speak(LONG, format=fmt, **conf)
    target = tmp_path / f"out.{fmt}"
    target.write_bytes(audio)
    assert len(server.requests) == 4
    single = _duration(one)
    # Joining copies the parts, so every part is in the file. mp3 carries a frame
    # of encoder padding per part, which adds a few hundredths of a second.
    assert 4 * single <= _duration(target) <= 4 * single + 0.25


@needs_ffmpeg
def test_broken_parts_raise_audio_error(monkeypatch, conf, server):
    monkeypatch.setattr("doc2speech.core.synthesize_chunk", lambda c, s, t: b"not audio")
    with pytest.raises(AudioError, match="could not join"):
        speak(LONG, **conf)


def test_empty_text(server, conf):
    with pytest.raises(EmptyTextError, match="Please enter some text"):
        speak("  \n\t ", **conf)
    assert server.requests == []


def test_control_characters_are_removed(server, conf):
    speak("Hello\x00 world\x07.", **conf)
    assert server.inputs == ["Hello world."]


def test_text_too_long(server, conf):
    with pytest.raises(LimitError, match=r"Text too long \(1,001 characters\)\. Please shorten \(max 1,000"):
        speak("a" * 1001, max_chars=1000, **conf)
    assert server.requests == []


def test_speak_file_writes_next_to_the_input(server, conf, tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("Hello from a file.", encoding="utf-8")
    written = speak_file(source, **conf)
    assert written == tmp_path / "notes.mp3"
    assert written.read_bytes() == SAMPLES["mp3"]


def test_speak_file_to_named_output(server, conf, tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("# Title\n\nSome **bold** text.", encoding="utf-8")
    out = tmp_path / "out" 
    out.mkdir()
    written = speak_file(source, out / "speech.wav", format="wav", **conf)
    assert written == out / "speech.wav"
    assert server.inputs == ["Title Some bold text."]


def test_speak_file_without_text(server, conf, tmp_path):
    source = tmp_path / "empty.txt"
    source.write_text("   \n", encoding="utf-8")
    with pytest.raises(EmptyTextError, match="No text found in empty.txt"):
        speak_file(source, **conf)


def test_speak_file_too_long(server, conf, tmp_path):
    source = tmp_path / "long.txt"
    source.write_text("a" * 50, encoding="utf-8")
    with pytest.raises(LimitError, match="Document too long .* Please split"):
        speak_file(source, max_chars=10, **conf)


def test_unsupported_file(conf, tmp_path):
    source = tmp_path / "slides.odp"
    source.write_bytes(b"x")
    with pytest.raises(UnsupportedFileError, match="not supported"):
        speak_file(source, **conf)


def test_missing_file(conf, tmp_path):
    with pytest.raises(UnsupportedFileError, match="File not found"):
        speak_file(tmp_path / "nope.txt", **conf)


# --- text extraction ---------------------------------------------------------

def test_extract_markdown(tmp_path):
    source = tmp_path / "a.md"
    source.write_text(
        "# Heading\n\nA [link](http://example.com) and `code`.\n\n```\nblock\n```\n\n![img](x.png)\n---\n",
        encoding="utf-8",
    )
    assert extract_text(source) == "Heading\n\nA link and ."


def test_extract_docx(tmp_path):
    source = make_docx(tmp_path / "a.docx", ["First paragraph.", "", "Second paragraph."])
    assert extract_text(source) == "First paragraph.\nSecond paragraph."


def test_extract_pdf(tmp_path):
    source = make_pdf(tmp_path / "a.pdf", ["First line of the PDF.", "Second line."])
    text = extract_text(source)
    assert "First line of the PDF." in text
    assert "Second line." in text


def test_extract_srt(tmp_path):
    source = tmp_path / "a.srt"
    source.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n\n2\n00:00:02,000 --> 00:00:03,000\nthere\n")
    assert extract_text(source) == "Hello there"


def test_extract_vtt(tmp_path):
    source = tmp_path / "a.vtt"
    source.write_text("WEBVTT\n\n00:01.000 --> 00:02.000\nHello\n\nNOTE x\n00:02.000 --> 00:03.000\nthere\n")
    assert extract_text(source) == "Hello there"


def test_extract_tex(tmp_path):
    source = tmp_path / "a.tex"
    source.write_text(
        "\\documentclass{article}\n\\begin{document}\n\\section{Intro}\nSome \\textbf{bold} text $x^2$. % note\n\\end{document}\n"
    )
    assert extract_text(source) == "Intro\nSome bold text ."


def test_markdown_must_be_utf8(tmp_path):
    source = tmp_path / "a.md"
    source.write_bytes("Gr\u00fc\u00dfe".encode("latin-1"))
    with pytest.raises(UnsupportedFileError, match="UTF-8"):
        extract_text(source)


def test_broken_docx(tmp_path):
    source = tmp_path / "a.docx"
    source.write_bytes(b"not a zip")
    with pytest.raises(UnsupportedFileError, match="cannot be read"):
        extract_text(source)

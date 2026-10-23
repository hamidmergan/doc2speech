import os

from conftest import SAMPLES

from doc2speech.cli import main


def args(server, *more):
    return ["--base-url", server.base_url, "--model", "m", "--voice", "alloy", *more]


def test_file_to_named_output(server, tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("Some notes.", encoding="utf-8")
    out = tmp_path / "notes.mp3"
    assert main([str(source), "-o", str(out), *args(server)]) == 0
    assert out.read_bytes() == SAMPLES["mp3"]


def test_file_default_output_next_to_input(server, tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("Some notes.", encoding="utf-8")
    assert main([str(source), *args(server)]) == 0
    assert (tmp_path / "notes.mp3").exists()


def test_generated_name_never_overwrites(server, tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("Some notes.", encoding="utf-8")
    for _ in range(3):
        assert main([str(source), *args(server)]) == 0
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["notes (1).mp3", "notes (2).mp3", "notes.mp3", "notes.txt"]


def test_explicit_output_is_overwritten(server, tmp_path):
    out = tmp_path / "x.mp3"
    out.write_bytes(b"old")
    assert main(["--text", "Hi.", "-o", str(out), *args(server)]) == 0
    assert out.read_bytes() == SAMPLES["mp3"]


def test_text_default_output(server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--text", "Hello there.", *args(server)]) == 0
    assert (tmp_path / "text.mp3").exists()
    assert server.inputs == ["Hello there."]


def test_format_and_speed(server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--text", "Hi.", "--format", "wav", "--speed", "1.1", *args(server)]) == 0
    assert (tmp_path / "text.wav").read_bytes() == SAMPLES["wav"]
    body = server.requests[0]["body"]
    assert body["response_format"] == "wav" and body["speed"] == 1.1


def test_format_from_environment_sets_the_name(server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DOC2SPEECH_FORMAT", "opus")
    assert main(["--text", "Hi.", *args(server)]) == 0
    assert (tmp_path / "text.opus").exists()


def test_language_spells_numbers(server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--text", "It was 47.", "--language", "en", *args(server)]) == 0
    assert server.inputs == ["It was forty-seven."]


def test_stdout(server, capfdbinary):
    assert main(["--text", "Hi.", "-o", "-", *args(server)]) == 0
    assert capfdbinary.readouterr().out == SAMPLES["mp3"]


def test_preview(server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--preview", "--language", "en", *args(server)]) == 0
    assert (tmp_path / "preview.mp3").exists()
    assert server.inputs[0].startswith("Hello!")


def test_voice_from_environment(server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DOC2SPEECH_VOICE", "nova")
    assert main(["--text", "Hi.", "--base-url", server.base_url, "--model", "m"]) == 0
    assert server.requests[0]["body"]["voice"] == "nova"


def test_both_inputs(server, tmp_path, capsys):
    source = tmp_path / "a.txt"
    source.write_text("x")
    assert main([str(source), "--text", "y", *args(server)]) == 2
    assert "either text or a file, not both" in capsys.readouterr().err


def test_no_input(server, capsys):
    assert main(args(server)) == 2
    assert "Please enter text or provide a file" in capsys.readouterr().err


def test_missing_configuration(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--text", "Hi."]) == 2
    err = capsys.readouterr().err
    assert "DOC2SPEECH_BASE_URL" in err and "DOC2SPEECH_MODEL" in err and "DOC2SPEECH_VOICE" in err
    assert os.listdir(tmp_path) == []


def test_missing_voice(server, capsys):
    assert main(["--text", "Hi.", "--base-url", server.base_url, "--model", "m"]) == 2
    assert "--voice" in capsys.readouterr().err


def test_server_error_exit_code(server, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    server.fail = True
    assert main(["--text", "Hi.", *args(server)]) == 1
    assert "Error:" in capsys.readouterr().err
    assert os.listdir(tmp_path) == []


def test_unsupported_file_exit_code(server, tmp_path, capsys):
    source = tmp_path / "a.xyz"
    source.write_text("x")
    assert main([str(source), *args(server)]) == 1
    assert "not supported" in capsys.readouterr().err


def test_help_is_english(capsys):
    import pytest

    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "Read text or a text file aloud" in out

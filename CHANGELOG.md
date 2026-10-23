# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-23

### Added

- `speak`, `speak_file`, `preview`, `split_text`, `extract_text` and `spell_numbers` as the public Python API.
- CLI `doc2speech` with `--text`, `--preview`, `-o`, `--voice`, `--speed`, `--format` and `--language`.
- Splitting of long texts at sentence boundaries, then at word boundaries, with a hard cut as the last resort.
- Parts are spoken in parallel and joined losslessly with the ffmpeg concat demuxer, in mp3, wav and opus.
- English numbers are spelled out as words before speaking. URLs, email addresses and digits inside words stay untouched.
- Text extraction from TXT, MD, DOCX, PDF (text layer), TEX, SRT and VTT.
- Settings from argument, environment variable or default, for any OpenAI-compatible `/audio/speech` server.
- Web page with `doc2speech serve`: text or document in, audio player and download out, with a voice preview.
- `Dockerfile` and `docker-compose.yml`, the image brings ffmpeg and starts the web page on port 8000.

[0.1.0]: https://github.com/hamidmergan/doc2speech/releases/tag/v0.1.0

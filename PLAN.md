# doc2speech

Reads text or a text file (TXT, MD, DOCX, PDF) aloud through an OpenAI-compatible `/audio/speech` endpoint. Long texts are split at sentence boundaries, generated piece by piece and joined losslessly with ffmpeg. Numbers are spelled out before speaking, because many voices stumble over digits.

Shape: Python library with a thin CLI and a small web UI. pip package `doc2speech`, Python package `doc2speech`. Other tools (doc2podcast, pptx-screencast) import it, so the public API stays small and stable: `speak`, `speak_file`, `split_text`.

## Decisions

- ffmpeg is a system requirement. It is checked before the first request whenever a text needs more than one part.

## Checklist

- [x] 0 Scaffold: repo, LICENSE (MIT), pyproject, package, tests, CI, PLAN.md, README skeleton, ffmpeg check.
- [ ] 1 Core: client, chunking, number words, joining with ffmpeg (concat demuxer), text extraction, `config.py`, `errors.py`.
- [ ] 2 API + CLI: `speak`, `speak_file`, `split_text`, CLI with `--voice`, `--text`, `--speed`, `--format`.
- [ ] 3 Tests with a fake server: splitting, number words (de and en), joining, CLI, missing configuration.
- [ ] 4 README, CHANGELOG 0.1.0, local smoke test with a real speech model.
- [ ] 5 English sweep, acceptance greps.
- [ ] 6 Web UI (`doc2speech serve`) and Docker.

## Open

- Nothing yet.

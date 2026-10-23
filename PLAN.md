# doc2speech

Reads text or a text file (TXT, MD, DOCX, PDF) aloud through an OpenAI-compatible `/audio/speech` endpoint. Long texts are split at sentence boundaries, generated piece by piece and joined losslessly with ffmpeg. Numbers are spelled out before speaking, because many voices stumble over digits.

Shape: Python library with a thin CLI and a small web UI. pip package `doc2speech`, Python package `doc2speech`. Other tools (doc2podcast, pptx-screencast) import it, so the public API stays small and stable: `speak`, `speak_file`, `split_text`.

## Decisions

- ffmpeg is a system requirement. It is checked before the first request whenever a text needs more than one part.
- Parts are joined with the ffmpeg concat demuxer and `-c copy`, no re-encoding. Tested for mp3, wav and opus. A single part is returned as it is.
- Defaults: 400 characters per request, 100,000 characters per text, 4 requests at once, 90 seconds per request, format mp3.
- Splitting looks for a sentence end in the last 40 percent of the limit, then for a word boundary, then cuts hard. Joining the parts gives back the text exactly.
- Numbers are spelled out for English only (`language` en, en-US, ...). Other languages stay unchanged, because the wrong reading of digits was only measured for English. Without a language nothing is changed.
- Speed is optional and only sent when set. Without it the request carries no speed field, because some servers slow a voice down with an audible echo.
- Text files: .txt, .md, .docx, .pdf (text layer), plus .tex, .srt and .vtt which need no extra dependency. Markdown, LaTeX and subtitle markup is stripped before speaking.
- Preview sentence for a voice in English and German, German for any other language.
- Not carried: provider catalog, default voice selection across several providers, voice fallback between providers, preview cache, job storage, resume of half-finished jobs, quotas. With one configured server these have no role. The voice is set per call and used for every part, so one output never mixes two voices.

## Checklist

- [x] 0 Scaffold: repo, LICENSE (MIT), pyproject, package, tests, CI, PLAN.md, README skeleton, ffmpeg check.
- [x] 1 Core: client, chunking, number words, joining with ffmpeg (concat demuxer), text extraction, `config.py`, `errors.py`.
- [ ] 2 API + CLI: `speak`, `speak_file`, `split_text`, CLI with `--voice`, `--text`, `--speed`, `--format`.
- [ ] 3 Tests with a fake server: splitting, number words (de and en), joining, CLI, missing configuration.
- [ ] 4 README, CHANGELOG 0.1.0, local smoke test with a real speech model.
- [ ] 5 English sweep, acceptance greps.
- [ ] 6 Web UI (`doc2speech serve`) and Docker.

## Open

- Nothing yet.

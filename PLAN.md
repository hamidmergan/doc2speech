# doc2speech

Reads text or a text file (TXT, MD, DOCX, PDF) aloud through an OpenAI-compatible `/audio/speech` endpoint. Long texts are split at sentence boundaries, generated piece by piece and joined losslessly with ffmpeg. Numbers are spelled out before speaking, because many voices stumble over digits.

Shape: Python library with a thin CLI and a small web UI. pip package `doc2speech`, Python package `doc2speech`. Other tools (doc2podcast, pptx-screencast) import it, so the public API stays small and stable: `speak`, `speak_file`, `split_text`.

## Decisions

- ffmpeg is a system requirement. It is checked before the first request whenever a text needs more than one part.
- Parts are joined with the ffmpeg concat demuxer and `-c copy`, no re-encoding. Tested for mp3, wav and opus. A single part is returned as it is.
- Defaults: 400 characters per request, 100,000 characters per text, 4 requests at once, 90 seconds per request, format mp3.
- Splitting looks for a sentence end in the last 40 percent of the limit, then for a word boundary, then cuts hard. Joining the parts gives back the text exactly.
- Joined mp3 keeps a frame of encoder padding per part, a few hundredths of a second. Lossless joining cannot avoid it and it is not audible.
- Numbers are spelled out for English only (`language` en, en-US, ...). Other languages stay unchanged, because the wrong reading of digits was only measured for English. Without a language nothing is changed.
- Speed is optional and only sent when set. Without it the request carries no speed field, because some servers slow a voice down with an audible echo.
- Text files: .txt, .md, .docx, .pdf (text layer), plus .tex, .srt and .vtt which need no extra dependency. Markdown, LaTeX and subtitle markup is stripped before speaking.
- `speak`, `speak_file` and `file_audio` take an optional `progress(done, total)` callback. The web page uses it to show which part is being spoken.
- Public API: `speak(text, voice, base_url, model, api_key=None, **settings) -> bytes`, `speak_file(path, output=None, voice, ...) -> Path`, `split_text(text, max_chars=None) -> list`, plus `preview`, `extract_text`, `spell_numbers`. Further settings are keyword arguments.
- The voice has no default. It is required by argument, `--voice` or `DOC2SPEECH_VOICE`, together with base_url and model.
- CLI: a file or `--text`, not both. `--preview` speaks the example sentence. `-o -` writes to stdout. Generated output names never overwrite (`notes (1).mp3`), an explicit `-o` does. Exit code 2 for configuration errors, 1 for other errors.
- Limits messages follow the original wording: "Text too long (... characters). Please shorten (max ... characters)." and "Document too long ... Please split ...".
- Preview sentence for a voice in English and German, German for any other language.
- Not carried: provider catalog, default voice selection across several providers, voice fallback between providers, preview cache, job storage, resume of half-finished jobs, quotas. With one configured server these have no role. The voice is set per call and used for every part, so one output never mixes two voices.

## Deliberate deviations from the source

- A dot in an English number is read as a decimal point, not as a thousands separator. The source stripped a dot from patterns like `3.141` and spoke "three thousand, one hundred and forty-one". Numbers are only spelled out for English (`_MEASURED_LANGUAGES = {"en"}`), and in English a dot is the decimal point, so that branch could only ever corrupt a number. The comma branch still covers English thousands (`1,000`).
- A failed request is tried again twice (`max_retries` 2). The source made exactly one attempt per part. A long text goes out in hundreds of parts, and one dropped connection would throw away the whole run, so the default allows two more attempts. `--max-retries 0` or `DOC2SPEECH_MAX_RETRIES=0` restores the single attempt, which is what a paid endpoint may want.

## Checklist

- [x] 0 Scaffold: repo, LICENSE (MIT), pyproject, package, tests, CI, PLAN.md, README skeleton, ffmpeg check.
- [x] 1 Core: client, chunking, number words, joining with ffmpeg (concat demuxer), text extraction, `config.py`, `errors.py`.
- [x] 2 API + CLI: `speak`, `speak_file`, `split_text`, CLI with `--voice`, `--text`, `--speed`, `--format`.
- [x] 3 Tests with a fake server: splitting, number words (de and en), joining, CLI, missing configuration.
- [x] 4 README, CHANGELOG 0.1.0, local smoke test with a real speech model.
- [x] 5 English sweep, acceptance greps.
- [x] 6 Web UI (`doc2speech serve`) and Docker.

## Open

- Web page: one job at a time, held in memory, nothing written to disk. Text or one uploaded file (max 25 MB), voice preview, audio player and download. Settings come from the environment and can be overwritten in the fields of the page. Host and origin guard like the other tools, no login.
- Docker image brings ffmpeg and starts the page on port 8000. `DOC2SPEECH_PORT` moves the published port if 8000 is taken.
- Smoke test with a real speech model: a 1,248 character text went out in four parts and came back as one 86 second mp3. Preview and wav also work.
- Possible extras later: speech providers with their own protocol instead of the OpenAI-compatible endpoint.

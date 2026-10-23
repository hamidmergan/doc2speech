# doc2speech

A lightweight Python utility that reads text and documents aloud with any OpenAI-compatible text-to-speech server. Long texts are split at sentence boundaries, spoken part by part and joined losslessly with ffmpeg, so a whole document comes back as one audio file.

doc2speech currently reads:

- Plain text (TXT, MD)
- Word documents (DOCX)
- PDF with a text layer
- LaTeX (TEX)
- Subtitles (SRT, VTT)

## Prerequisites

- Python 3.9 or newer
- ffmpeg on PATH. It joins the parts of a long text. A text short enough for one request works without it.
- A server with an OpenAI-compatible `/audio/speech` endpoint and a **text-to-speech model** (for example Kokoro, XTTS, Piper behind an OpenAI-compatible gateway, LM Studio or a cloud provider). A chat model is not enough.
- An API key is optional. Many self-hosted servers do not need one.

If you run your own model, your documents stay on your own network. Nothing leaves your machine or data center.

## Installation

```bash
pip install doc2speech
```

Alternatively, you can install it from the source:

```bash
git clone https://github.com/hamidmergan/doc2speech.git
cd doc2speech
pip install .
```

ffmpeg comes from your package manager, for example `brew install ffmpeg` or `apt install ffmpeg`.

## Usage

### Command-Line

Read a file aloud:

```bash
doc2speech notes.md --voice alloy --base-url http://localhost:11434/v1 --model your-speech-model
```

This writes `notes.mp3` next to `notes.md`. Use `-o` to choose the output:

```bash
doc2speech notes.md -o audio/notes.mp3 --voice alloy --base-url http://localhost:11434/v1 --model your-speech-model
```

Read a short text instead of a file:

```bash
doc2speech --text "Good morning, here is today's summary." --voice alloy --base-url http://localhost:11434/v1 --model your-speech-model
```

Pick a format and a speaking speed:

```bash
doc2speech notes.md --voice alloy --format wav --speed 1.1 --base-url ... --model ...
```

Hear what a voice sounds like before using it:

```bash
doc2speech --preview --voice nova --language en --base-url ... --model ...
```

Write the audio to stdout with `-o -`, for example to pipe it into a player:

```bash
doc2speech --text "Hello." --voice alloy -o - --base-url ... --model ... | ffplay -
```

A generated name never overwrites an existing file, a number is added instead (`notes (1).mp3`). A file named explicitly with `-o` is overwritten. Errors appear on stderr. The exit code is 2 for a configuration error and 1 for any other error.

### Python API

```python
from doc2speech import speak

audio = speak(
    "Good morning, here is today's summary.",
    voice="alloy",
    base_url="http://localhost:11434/v1",
    model="your-speech-model",
)
open("summary.mp3", "wb").write(audio)
```

Read a whole file and write the audio next to it:

```python
from doc2speech import speak_file

written = speak_file(
    "notes.md",
    voice="alloy",
    base_url="http://localhost:11434/v1",
    model="your-speech-model",
)
print(written)  # notes.mp3
```

`speak_file` overwrites an existing audio file, with a name you give and with the generated one. The CLI is more careful here: a name it generates itself never overwrites, it adds a number instead (`notes (1).mp3`). Check the path yourself if the library call needs the same rule.

`speak`, `speak_file` and `preview` also take `client=`, a ready-made OpenAI client, for example to share one connection pool across many calls:

```python
from openai import OpenAI

from doc2speech import speak

client = OpenAI(base_url="http://localhost:11434/v1", api_key="none")
audio = speak(
    "Hello.",
    voice="alloy",
    base_url="http://localhost:11434/v1",
    model="your-speech-model",
    client=client,
)
```

A client given this way is used as it is. `base_url`, `api_key`, `timeout` and `max_retries` from the settings are then ignored, the client you built decides them. `voice`, `model`, `format`, `speed` and `language` still apply, and `base_url`, `model` and `voice` are still required, because the settings are resolved before the client is used.

The public API is small and stable, so other tools can build on it:

| Function | Returns |
| --- | --- |
| `speak(text, voice=..., base_url=..., model=..., api_key=None, **settings)` | the audio as `bytes` |
| `speak_file(path, output=None, voice=..., ...)` | the written `Path` |
| `preview(voice, language=None, ...)` | a short example sentence as `bytes` |
| `split_text(text, max_chars=None)` | the parts as a `list` of strings |
| `extract_text(path)` | the text of a file as `str` |
| `spell_numbers(text, language)` | the text with numbers as words |

A few helpers are exported for tools that build on doc2speech: `file_audio(path, settings)` voices an already resolved file run, `extract_bytes(name, data)` reads an upload that is only in memory, `supported_suffixes()` lists the readable extensions, `preview_text(language)` gives the example sentence, `SUFFIXES` maps a format to its file extension, and `Settings` together with `resolve(**settings)` builds the settings themselves.

`split_text` returns exactly the parts `speak` would send. Without `max_chars` it takes the limit from `DOC2SPEECH_MAX_CHARS_PER_CHUNK`, otherwise 400, so a part count shown before a run matches the run.

Every setting from the table below can be passed to `speak`, `speak_file` and `preview` as a keyword argument. Errors are raised as subclasses of `SpeechError`: `ConfigError`, `LimitError`, `EmptyTextError`, `UnsupportedFileError`, `ModelError` and `AudioError`.

`ModelError` says what the server answered. `status` is the HTTP status code as an `int`, or `None` when the request never reached an answer, for example on a timeout or a refused connection. `transient` says whether sending the same request again can still succeed: a timeout or a connection failure counts as transient, and so do 408, 429 and every 5xx. Every other answer is final, the request itself has to change before it can work. Both are there so a tool built on doc2speech can decide without reading the message text.

```python
import time

from doc2speech import ModelError, speak

for attempt in range(4):
    try:
        audio = speak(
            "Hello.",
            voice="alloy",
            base_url="http://localhost:11434/v1",
            model="your-speech-model",
        )
        break
    except ModelError as exc:
        if not exc.transient or attempt == 3:
            raise
        print(f"server said {exc.status}, trying again")
        time.sleep(2 ** attempt)
```

`RETRY_STATUS` is exported too, the set of non 5xx codes that count as transient, in case a caller wants to show them.

### Settings

Order: argument, then environment variable, then default.

| Argument / flag | Environment variable | Default |
| --- | --- | --- |
| `base_url` / `--base-url` | `DOC2SPEECH_BASE_URL` | none, required |
| `model` / `--model` | `DOC2SPEECH_MODEL` | none, required |
| `voice` / `--voice` | `DOC2SPEECH_VOICE` | none, required |
| `api_key` / `--api-key` | `DOC2SPEECH_API_KEY` (then `OPENAI_API_KEY`) | optional |
| `speed` / `--speed` | `DOC2SPEECH_SPEED` | not sent |
| `format` / `--format` | `DOC2SPEECH_FORMAT` | `mp3` (also `wav`, `opus`) |
| `language` / `--language` | `DOC2SPEECH_LANGUAGE` | none |
| `max_chars_per_chunk` / `--max-chars-per-chunk` | `DOC2SPEECH_MAX_CHARS_PER_CHUNK` | 400 characters |
| `max_chars` / `--max-chars` | `DOC2SPEECH_MAX_CHARS` | 100000 characters |
| `concurrency` / `--concurrency` | `DOC2SPEECH_CONCURRENCY` | 4 |
| `timeout` / `--timeout` | `DOC2SPEECH_TIMEOUT` | 90 seconds |
| `max_retries` / `--max-retries` | `DOC2SPEECH_MAX_RETRIES` | 2 extra attempts |

The voice has no default, because voice names differ from server to server. There is no default base URL or model either, so nothing is sent anywhere you did not name. The base URL works with or without the trailing `/v1`, both reach the same endpoint.

Speed is only sent when you set it. Some servers add an audible echo to a slowed-down voice, so the request carries no speed field by default.

With `language` set to English, numbers are spelled out before speaking (`47` becomes `forty-seven`, `1986` becomes `nineteen eighty-six`), because many voices read digits in the wrong language. Other languages stay untouched. URLs, email addresses and digits inside words such as `COVID-19` are never changed.

If a limit is exceeded, the text is rejected with a message naming the limit and the setting. Nothing is silently truncated.

### Web UI

A small page in the browser, with the same voices and settings as the CLI:

```bash
pip install "doc2speech[ui]"
doc2speech serve
```

Then open http://127.0.0.1:8000. Paste a text or drop a document, pick a voice, press Create audio. The result plays on the page and can be downloaded. Preview voice speaks a short example sentence so you can compare voices first.

Base URL, model, voice and the rest come from the environment and can be changed in the fields of the page. Empty fields keep the value the server was started with.

The page has no login. It listens on 127.0.0.1 by default, so only your own machine can reach it. Use `--host 0.0.0.0` only in a network you trust, for example inside Docker behind your own reverse proxy.

```bash
doc2speech serve --host 0.0.0.0 --port 8000 --voice alloy
```

### Docker

The image brings ffmpeg and starts the web page:

```bash
docker compose up
```

The page is then on http://127.0.0.1:8000. Settings come from `DOC2SPEECH_*` environment variables, `docker-compose.yml` lists them all:

```bash
DOC2SPEECH_BASE_URL=http://host.docker.internal:11434/v1 \
DOC2SPEECH_MODEL=your-speech-model \
DOC2SPEECH_VOICE=alloy \
docker compose up
```

A speech server running on your own machine is reachable from inside the container as `host.docker.internal`, not as `localhost`. If port 8000 is taken, set `DOC2SPEECH_PORT`.

The CLI works in the image too:

```bash
docker compose run --rm doc2speech doc2speech --text "Hello." --voice alloy -o -
```

## Limitations

Quality depends on the chosen model and voice. Check important results.

PDFs are read from their text layer. A scan without a text layer gives no text, run OCR on it first.

Joining the parts of a long text needs ffmpeg and copies the audio without re-encoding. In mp3 each part keeps a frame of encoder padding, which adds a few hundredths of a second per part.

## Running Tests

```bash
pip install -e ".[test]"
pytest
```

The tests run against a local fake server and need no real model. Tests that join audio are skipped when ffmpeg is missing.

## License

MIT

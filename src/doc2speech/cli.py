import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .audio import SUFFIXES
from .config import FORMATS, resolve
from .core import file_audio, preview, speak
from .errors import ConfigError, SpeechError

LOOPBACK = ("127.0.0.1", "localhost", "::1")

UI_HINT = (
    "The web page needs the extra packages. Install them with "
    "'pip install \"doc2speech[ui]\"'."
)

NO_LOGIN = (
    "Warning: the page has no login. On an address other than 127.0.0.1 "
    "everyone who can reach it can use your speech server."
)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="doc2speech",
        description="Read text or a text file aloud with an OpenAI-compatible text-to-speech server.",
        epilog="Example: doc2speech notes.md --voice alloy. "
        "Run 'doc2speech serve' for the web page.",
    )
    p.add_argument("file", nargs="?", help="Text file: .txt, .md, .docx, .pdf, .tex, .srt or .vtt")
    p.add_argument("--text", help="Text to read aloud instead of a file")
    p.add_argument("--preview", action="store_true", help="Speak a short example sentence with the voice")
    p.add_argument(
        "-o",
        "--output",
        help="Output file, '-' for stdout. Default: <name>.<format> next to the input "
        "(text.<format> for --text, preview.<format> for --preview)",
    )
    p.add_argument("--voice", help="Voice of the speech model, e.g. alloy (required)")
    p.add_argument("--speed", type=float, help="Speaking speed, e.g. 0.9 or 1.2. Default: not sent")
    p.add_argument("--format", choices=FORMATS, help="Audio format (default mp3)")
    p.add_argument(
        "--language",
        help="Language of the text, e.g. en or de. English numbers are spelled out as words",
    )
    p.add_argument("--base-url", help="URL of the OpenAI-compatible server, e.g. http://localhost:11434/v1")
    p.add_argument("--model", help="Name of the text-to-speech model")
    p.add_argument("--api-key", help="API key, if the server requires one")
    p.add_argument("--max-chars-per-chunk", type=int, help="Characters per request (default 400)")
    p.add_argument("--max-chars", type=int, help="Longest accepted text in characters (default 100000)")
    p.add_argument("--concurrency", type=int, help="Requests at the same time (default 4)")
    p.add_argument("--timeout", type=float, help="Seconds per request (default 90)")
    p.add_argument("--max-retries", type=int, help="Extra attempts after a failed request (default 2)")
    p.add_argument("--version", action="version", version=f"doc2speech {__version__}")
    return p


def _serve_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="doc2speech serve", description="Start the local web page.")
    p.add_argument("--host", default="127.0.0.1", help="Default: 127.0.0.1 (this computer only)")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--voice", help="Voice the page starts with")
    p.add_argument("--speed", type=float, help="Speaking speed the page starts with")
    p.add_argument("--format", choices=FORMATS, help="Audio format the page starts with")
    p.add_argument("--language", help="Language the page starts with")
    p.add_argument("--base-url", help="URL of the OpenAI-compatible server")
    p.add_argument("--model", help="Name of the text-to-speech model")
    p.add_argument("--api-key", help="API key, if the server requires one")
    return p


def _serve(argv: List[str]) -> int:
    args = _serve_parser().parse_args(argv)
    try:
        import uvicorn

        from .web.app import create_app
    except ImportError:
        print(UI_HINT, file=sys.stderr)
        return 2
    # The page works without settings too, they can be typed into its fields.
    try:
        settings = resolve(
            voice=args.voice, base_url=args.base_url, model=args.model, api_key=args.api_key,
            speed=args.speed, format=args.format, language=args.language,
        )
    except ConfigError:
        settings = None
    app = create_app(
        settings,
        # on loopback, only accept our own host names, so other web pages cannot reach it via DNS rebinding
        allowed_hosts=list(LOOPBACK) if args.host in LOOPBACK else None,
    )
    if args.host not in LOOPBACK:
        print(NO_LOGIN, file=sys.stderr)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def _free(path: Path) -> Path:
    """Return path, or 'name (1).mp3', 'name (2).mp3', ... if it already exists."""
    candidate, n = path, 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        n += 1
    return candidate


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "serve":
        return _serve(argv[1:])
    args = _parser().parse_args(argv)
    has_file = bool(args.file)
    has_text = args.text is not None

    if has_file and has_text:
        print("Please provide either text or a file, not both.", file=sys.stderr)
        return 2
    if args.preview and (has_file or has_text):
        print("--preview cannot be combined with a file or --text.", file=sys.stderr)
        return 2
    if not (has_file or has_text or args.preview):
        print("Please enter text or provide a file.", file=sys.stderr)
        return 2

    options = dict(
        voice=args.voice,
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        speed=args.speed,
        format=args.format,
        language=args.language,
        max_chars_per_chunk=args.max_chars_per_chunk,
        max_chars=args.max_chars,
        concurrency=args.concurrency,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )
    to_stdout = args.output == "-"

    try:
        settings = resolve(**options)
        suffix = SUFFIXES[settings.format]
        if args.preview:
            options.pop("speed")
            audio = preview(**options)
            default = Path("preview" + suffix)
        elif has_text:
            audio = speak(args.text, **options)
            default = Path("text" + suffix)
        else:
            source = Path(args.file)
            audio = file_audio(source, settings)
            default = source.with_suffix(suffix)
    except ConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except SpeechError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if to_stdout:
        sys.stdout.buffer.write(audio)
        sys.stdout.buffer.flush()
        return 0
    # an explicitly named output file is overwritten, generated names never are
    target = Path(args.output) if args.output else _free(default)
    target.write_bytes(audio)
    print(f"Wrote {target}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

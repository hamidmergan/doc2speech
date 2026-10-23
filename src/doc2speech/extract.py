"""Text extraction for speech output, from bytes or from a path."""

import re
from io import BytesIO
from pathlib import Path
from typing import Callable, Dict, List, Union

from .errors import UnsupportedFileError

Source = Union[bytes, str, Path]


def _as_bytes(src: Source) -> bytes:
    """Raw bytes for the text formats, which have to decode the whole thing anyway."""
    if isinstance(src, bytes):
        return src
    with open(src, "rb") as f:
        return f.read()


def _as_stream(src: Source):
    """What python-docx should open: a path stays a path."""
    return BytesIO(src) if isinstance(src, bytes) else src


def sanitize_text(raw: str) -> str:
    """Normalize free-form pasted text: unify line ends, drop control characters."""
    cleaned = raw.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "".join(
        ch for ch in cleaned
        if ch in ("\t", "\n") or (ord(ch) >= 32 and ord(ch) != 127)
    )
    return cleaned.strip()


def extract_text_md(content: Source) -> str:
    text = _as_bytes(content).decode("utf-8")
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    # Convert links to just the link text
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # Remove headings markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_tex(content: Source) -> str:
    text = _as_bytes(content).decode("utf-8")
    # Remove comments
    text = re.sub(r"(?<!\\)%.*$", "", text, flags=re.MULTILINE)
    # Remove preamble (everything before \begin{document})
    match = re.search(r"\\begin\{document\}", text)
    if match:
        text = text[match.end():]
    # Remove \end{document}
    text = re.sub(r"\\end\{document\}", "", text)
    # Remove math environments
    text = re.sub(r"\$\$[\s\S]*?\$\$", "", text)
    text = re.sub(r"\$[^$]+\$", "", text)
    text = re.sub(r"\\\[[\s\S]*?\\\]", "", text)
    text = re.sub(r"\\\(.*?\\\)", "", text)
    # Remove verbatim/lstlisting environments
    text = re.sub(
        r"\\begin\{(verbatim|lstlisting|minted)\}[\s\S]*?\\end\{\1\}", "", text
    )
    # Convert common text commands to their content
    text = re.sub(r"\\(?:textbf|textit|emph|underline|texttt)\{([^}]*)\}", r"\1", text)
    # Convert section commands to their titles
    text = re.sub(
        r"\\(?:section|subsection|subsubsection|chapter|paragraph|subparagraph)\*?\{([^}]*)\}",
        r"\1",
        text,
    )
    # Remove remaining commands (but keep their mandatory argument text for some)
    text = re.sub(r"\\(?:label|ref|cite|url|href|includegraphics)\{[^}]*\}", "", text)
    # Remove \begin{...} and \end{...}
    text = re.sub(r"\\(?:begin|end)\{[^}]*\}", "", text)
    # Remove remaining backslash commands without braces
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)
    # Remove braces
    text = re.sub(r"[{}]", "", text)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_docx(content: Source) -> str:
    from docx import Document

    doc = Document(_as_stream(content))
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_text_pdf(content: Source) -> str:
    """The text layer of every page. A scanned PDF without text layer yields nothing."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(content if isinstance(content, bytes) else str(content))
    try:
        pages = []
        for index in range(len(pdf)):
            page = pdf[index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range().replace("\r\n", "\n").replace("\r", "\n")
                finally:
                    textpage.close()
            finally:
                page.close()
            if text.strip():
                pages.append(text.strip())
        return "\n".join(pages)
    finally:
        pdf.close()


def extract_text_txt(content: Source) -> str:
    return _as_bytes(content).decode("utf-8", errors="replace")


def extract_text_srt(content: Source) -> str:
    lines = []
    for line in _as_bytes(content).decode("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^\d+$", stripped):
            continue
        if re.match(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}", stripped):
            continue
        lines.append(stripped)
    return " ".join(lines)


def extract_text_vtt(content: Source) -> str:
    lines = []
    for line in _as_bytes(content).decode("utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("WEBVTT") or stripped.startswith("NOTE"):
            continue
        if re.match(r"^\d+$", stripped):
            continue
        if re.match(r"[\d:]+\.\d{3}\s*-->\s*[\d:]+\.\d{3}", stripped):
            continue
        lines.append(stripped)
    return " ".join(lines)


EXTRACTORS: Dict[str, Callable[[Source], str]] = {
    ".txt": extract_text_txt,
    ".md": extract_text_md,
    ".docx": extract_text_docx,
    ".pdf": extract_text_pdf,
    ".tex": extract_text_tex,
    ".srt": extract_text_srt,
    ".vtt": extract_text_vtt,
}


def supported_suffixes() -> List[str]:
    return sorted(EXTRACTORS)


def _extractor(suffix: str) -> Callable[[Source], str]:
    found = EXTRACTORS.get(suffix)
    if found is None:
        raise UnsupportedFileError(
            f"File type {suffix or '(no extension)'} is not supported. "
            f"Allowed: {', '.join(supported_suffixes())}"
        )
    return found


def _run(extractor: Callable[[Source], str], source: Source, name: str) -> str:
    try:
        return extractor(source)
    except UnicodeDecodeError:
        raise UnsupportedFileError(f"{name} is not UTF-8 text.")
    except Exception as exc:
        raise UnsupportedFileError(f"{name} cannot be read: {exc}")


def extract_text(path: Union[str, Path]) -> str:
    """Read the text of a supported file."""
    path = Path(path)
    if not path.is_file():
        raise UnsupportedFileError(f"File not found: {path}")
    suffix = path.suffix.lower()
    return _run(_extractor(suffix), path, path.name)


def extract_bytes(name: str, data: bytes) -> str:
    """Read the text of an uploaded file, the type comes from its name."""
    suffix = Path(name).suffix.lower()
    return _run(_extractor(suffix), data, Path(name).name or "the file")

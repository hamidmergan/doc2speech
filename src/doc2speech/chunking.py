"""Split long texts into parts a speech server can voice in one request."""

from typing import List, Optional

from .config import chunk_limit

# From which share of the ceiling on a sentence end is looked for.
_SEARCH_FROM = 0.6

_SENTENCE_ENDS = (". ", "! ", "? ", ".\n", "!\n", "?\n")


def split_text(text: str, max_chars: Optional[int] = None) -> List[str]:
    """Split long text, preferably at sentence ends, otherwise at word boundaries.

    Joining the parts gives back the original text exactly. No part is longer
    than max_chars. Without max_chars the limit comes from
    DOC2SPEECH_MAX_CHARS_PER_CHUNK, otherwise it is 400, so the parts are the
    ones `speak` would send.
    """
    limit = max_chars or chunk_limit()
    if len(text) <= limit:
        return [text]

    search_from = max(1, int(limit * _SEARCH_FROM))
    chunks: List[str] = []
    remaining = text

    while len(remaining) > limit:
        split_at = -1
        for punct in _SENTENCE_ENDS:
            pos = remaining.rfind(punct, search_from, limit)
            if pos != -1:
                split_at = pos + len(punct)
                break
        if split_at == -1:
            # No sentence end in reach: split at the last word boundary.
            pos = remaining.rfind(" ", search_from, limit)
            if pos != -1:
                split_at = pos + 1
        if split_at == -1:
            split_at = limit  # a single word is longer than the limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:]

    if remaining:
        chunks.append(remaining)

    return chunks

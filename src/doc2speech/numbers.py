"""Digits to words before the text goes to the voice."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Digit sequence with thousands separators and a decimal, standing alone as a word.
_NUMBER = re.compile(r"(?<![\w.,/@-])(?:\d{1,3}(?:[.,]\d{3})+|\d+(?:\.\d+)?)(?![\w/@-])")

# Addresses stay untouched, a digit there is not a spoken number.
_ADDRESS = re.compile(r"\S+(?:://|@)\S+|\b\S+\.(?:de|com|org|net|eu|io)\b", re.I)

# Four-digit numbers in this range are spoken as a year.
_YEAR_FROM, _YEAR_TO = 1500, 2099

# Voices guess their language from the text and read digits in the wrong
# language. This was measured for English only, elsewhere nothing changes.
_MEASURED_LANGUAGES = {"en"}


def language_code(language: Optional[str]) -> str:
    """'EN-US' becomes 'en'."""
    return (language or "").strip().replace("_", "-").split("-")[0].lower()


def _as_words(raw: str, lang: str) -> str:
    from num2words import num2words

    # A comma groups the thousands. A dot is the decimal point, never a group,
    # because digits are only spelled out for English.
    text = raw.replace(",", "") if re.fullmatch(r"\d{1,3}(?:,\d{3})+", raw) else raw
    number = float(text) if "." in text else int(text)
    if isinstance(number, int) and _YEAR_FROM <= number <= _YEAR_TO and len(raw) == 4:
        return num2words(number, lang=lang, to="year")
    return num2words(number, lang=lang)


def spell_numbers(text: Optional[str], language: Optional[str]) -> str:
    """Spell digits out as words, English only."""
    if not text:
        return ""
    lang = language_code(language)
    if lang not in _MEASURED_LANGUAGES:
        return text
    try:
        from num2words import CONVERTER_CLASSES
    except ImportError:
        logger.warning("num2words is missing, digits go to the voice unchanged")
        return text
    if lang not in CONVERTER_CLASSES:
        return text

    protected = [(m.start(), m.end()) for m in _ADDRESS.finditer(text)]

    def replace(match: "re.Match") -> str:
        if any(a <= match.start() < b for a, b in protected):
            return match.group(0)
        try:
            return _as_words(match.group(0), lang)
        except Exception:  # an unreadable number stays as it is
            return match.group(0)

    return _NUMBER.sub(replace, text)

"""The short example sentence a voice introduces itself with."""

_SENTENCE = {
    "en": "Hello! This is a preview of the selected voice. I hope you enjoy the sound.",
    "de": "Hallo! Dies ist eine Vorschau der ausgewählten Stimme. Ich hoffe, sie gefällt Ihnen.",
}


def preview_text(lang: str) -> str:
    """The preview sentence in this language, otherwise the German one."""
    return _SENTENCE.get(lang, _SENTENCE["de"])

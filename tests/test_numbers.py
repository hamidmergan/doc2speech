"""Digits go to the voice as words, otherwise it reads them in the wrong language."""

import pytest

from doc2speech import spell_numbers


@pytest.mark.parametrize("raw, expected", [
    ("The result was 47.", "The result was forty-seven."),
    ("published in 1986.", "published in nineteen eighty-six."),
    ("A 2016 study from a university.", "A twenty sixteen study from a university."),
    ("reached 13.3 points", "reached thirteen point three points"),
    ("from ITD 5, WPM INF", "from ITD five, WPM INF"),
    ("80 percent of students", "eighty percent of students"),
    ("about 1,000 participants", "about one thousand participants"),
])
def test_english_numbers_are_spelled_out(raw, expected):
    assert spell_numbers(raw, "EN") == expected


@pytest.mark.parametrize("language", ["DE", "de", "de-DE", "FR", "TR", "ES"])
def test_other_languages_stay_untouched(language):
    """Measured for English only, German and every other language stay as they are."""
    text = "Es waren 47 Personen im Jahr 1986."
    assert spell_numbers(text, language) == text


def test_language_variants_are_recognized():
    assert spell_numbers("was 47.", "EN-US") == "was forty-seven."
    assert spell_numbers("was 47.", "en_GB") == "was forty-seven."
    assert spell_numbers("was 47.", "en") == "was forty-seven."


def test_text_without_digits_stays_the_same():
    text = "There is nothing to convert in this sentence."
    assert spell_numbers(text, "EN") == text


def test_unknown_language_leaves_the_text_alone():
    text = "The result was 47."
    assert spell_numbers(text, "xx") == text
    assert spell_numbers(text, "") == text
    assert spell_numbers(text, None) == text


@pytest.mark.parametrize("text", [
    "Test yourself at https://news-test.de/ today.",
    "See https://example.com/2016/report for details.",
    "Write to a1@example.org please.",
])
def test_addresses_stay_untouched(text):
    assert spell_numbers(text, "EN") == text


def test_digits_inside_words_stay():
    """COVID-19 or H2O are names, not numbers."""
    assert spell_numbers("The COVID-19 pandemic and H2O.", "EN") == "The COVID-19 pandemic and H2O."


def test_empty_text_does_not_fail():
    assert spell_numbers("", "EN") == ""
    assert spell_numbers(None, "EN") == ""

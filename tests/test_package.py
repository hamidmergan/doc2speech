import doc2speech


def test_version():
    assert doc2speech.__version__ == "0.1.0"


def test_every_exported_name_exists():
    for name in doc2speech.__all__:
        assert hasattr(doc2speech, name), name


def test_the_helpers_other_tools_need_are_exported():
    """Importing from doc2speech.extract or doc2speech.config stays unnecessary."""
    for name in ("extract_bytes", "supported_suffixes", "file_audio", "Settings",
                 "resolve", "preview_text", "SUFFIXES"):
        assert name in doc2speech.__all__, name

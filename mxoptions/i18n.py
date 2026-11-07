"""Tiny translation layer: English source strings. No other catalogue is shipped; _() is kept as the hook."""

_catalogue = {}
language = "en"


def setup(preferred="auto"):
    """Kept for callers that pass the configured language; English is the only one."""
    global _catalogue, language
    language = "en"
    _catalogue = {}


def _(text):
    return _catalogue.get(text, text)

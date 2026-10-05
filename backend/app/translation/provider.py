import os
from typing import Protocol

SUPPORTED_LANGUAGES = {"en", "hi", "te", "ta", "kn", "ml", "mr", "bn"}

def detect_language(text: str) -> str:
    """Detect the dominant supported writing system without claiming model-level language certainty."""
    buckets = {"hi": 0, "te": 0, "ta": 0, "kn": 0, "ml": 0, "bn": 0, "en": 0}
    for char in text:
        code = ord(char)
        if 0x0900 <= code <= 0x097F: buckets["hi"] += 1
        elif 0x0C00 <= code <= 0x0C7F: buckets["te"] += 1
        elif 0x0B80 <= code <= 0x0BFF: buckets["ta"] += 1
        elif 0x0C80 <= code <= 0x0CFF: buckets["kn"] += 1
        elif 0x0D00 <= code <= 0x0D7F: buckets["ml"] += 1
        elif 0x0980 <= code <= 0x09FF: buckets["bn"] += 1
        elif ("A" <= char <= "Z") or ("a" <= char <= "z"): buckets["en"] += 1
    detected, count = max(buckets.items(), key=lambda item: item[1])
    return detected if count else "und"

class TranslationProvider(Protocol):
    name: str
    configured: bool
    def translate(self, text: str, target_language: str) -> str: ...

class UnconfiguredTranslationProvider:
    name = os.getenv("TRANSLATION_PROVIDER", "none")
    configured = False
    def translate(self, text: str, target_language: str) -> str: raise RuntimeError("Translation provider is not configured")

def get_translation_provider() -> TranslationProvider:
    return UnconfiguredTranslationProvider()

import os
from typing import Protocol

SUPPORTED_LANGUAGES = {"en", "hi", "te", "ta", "kn", "ml", "mr", "bn"}

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

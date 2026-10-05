import os
from typing import Protocol

class TranscriptionProvider(Protocol):
    name: str
    configured: bool
    def transcribe(self, file_path: str) -> list[dict[str, str]]: ...

class UnconfiguredTranscriptionProvider:
    name = os.getenv("TRANSCRIPTION_PROVIDER", "none")
    configured = False
    def transcribe(self, file_path: str) -> list[dict[str, str]]: raise RuntimeError("Transcription provider is not configured")

def get_transcription_provider() -> TranscriptionProvider:
    return UnconfiguredTranscriptionProvider()

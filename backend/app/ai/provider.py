from dataclasses import dataclass
import os
from typing import Protocol

class AIProvider(Protocol):
    name: str
    configured: bool
    def analyze(self, transcript: str) -> dict: ...
    def answer(self, question: str, transcript: str) -> dict: ...

@dataclass
class DemoAIProvider:
    name: str = "demo"
    configured: bool = True
    def analyze(self, transcript: str) -> dict:
        return {"summary": "Demo analysis is grounded in the supplied transcript.", "decisions": [], "actions": [], "risks": [], "evidence_required": True}
    def answer(self, question: str, transcript: str) -> dict:
        return {"answer": "I couldn't find sufficient evidence in this meeting.", "confidence": 0.2, "evidence": []}

class UnconfiguredAIProvider:
    name = os.getenv("AI_PROVIDER", "openai")
    configured = False
    def analyze(self, transcript: str) -> dict: raise RuntimeError("AI provider not configured")
    def answer(self, question: str, transcript: str) -> dict: raise RuntimeError("AI provider not configured")

def get_ai_provider() -> AIProvider:
    return DemoAIProvider() if os.getenv("AI_PROVIDER", "demo") == "demo" else UnconfiguredAIProvider()

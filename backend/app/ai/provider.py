from dataclasses import dataclass
import os
import json
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

class OpenAIProvider:
    name = "openai"
    configured = True
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "30")))
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")
    def _json(self, system: str, user: str) -> dict:
        response = self.client.chat.completions.create(model=self.model, temperature=0, response_format={"type":"json_object"}, messages=[{"role":"system","content":system},{"role":"user","content":user}])
        return json.loads(response.choices[0].message.content or "{}")
    def analyze(self, transcript: str) -> dict:
        from .prompts.summary import SYSTEM_PROMPT
        return self._json(SYSTEM_PROMPT, transcript)
    def answer(self, question: str, transcript: str) -> dict:
        from .prompts.qa import SYSTEM_PROMPT
        return self._json(SYSTEM_PROMPT, f"Question: {question}\nTranscript:\n{transcript}")

def get_ai_provider() -> AIProvider:
    if os.getenv("AI_PROVIDER", "demo") == "demo": return DemoAIProvider()
    if os.getenv("AI_PROVIDER") == "openai" and os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider()
    return UnconfiguredAIProvider()

from dataclasses import dataclass
import os
import json
import re
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
        segments = []
        for line in transcript.splitlines():
            match = re.match(r"\[(?P<timestamp>[^]]+)\]\s*(?P<speaker>[^:]+):\s*(?P<text>.+)", line.strip())
            if match: segments.append(match.groupdict())
        decisions, actions, risks, questions = [], [], [], []
        for item in segments:
            text, lower = item["text"].strip(), item["text"].lower()
            evidence = text
            base = {"speaker": item["speaker"].strip(), "timestamp": item["timestamp"], "evidence": evidence}
            if "decision:" in lower or lower.startswith("we should ") or lower.startswith("use "):
                decisions.append({"decision": text.removeprefix("Decision: ").strip(), **base, "confidence": 0.82})
            if "i will " in lower or "i can own " in lower:
                task = text.split("I will ", 1)[-1].split("I can own ", 1)[-1].strip().rstrip(".")
                actions.append({"task": task, "owner": base["speaker"], "deadline": "Not specified in the meeting", "priority": "Medium", "status": "Pending", **base, "confidence": 0.78})
            if any(term in lower for term in ("cannot", "pending", "missing", "risk")):
                risks.append({"risk": text, "severity": "High" if "cannot" in lower or "missing" in lower else "Medium", "recommendation": "Confirm an owner and next step.", **base})
            if "?" in text or lower.startswith("open question"):
                questions.append({"question": text, **base})
        summary = " ".join(item["text"] for item in segments[:2]) or "No transcript evidence was supplied."
        return {"summary": summary, "decisions": decisions, "actions": actions, "risks": risks, "questions": questions, "evidence_required": True}
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

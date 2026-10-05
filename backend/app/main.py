from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated
import os
import jwt
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel, Field

app = FastAPI(title="MeetMind AI API", version="1.0.0", description="Evidence-based meeting intelligence API")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET = os.getenv("JWT_SECRET", "dev-only-change-me")

class UserCredentials(BaseModel):
    email: str
    password: str = Field(min_length=8)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)

class Status(str, Enum):
    pending = "Pending"
    progress = "In progress"
    blocked = "Blocked"
    completed = "Completed"

USERS: dict[str, str] = {}
DEMO_MEETING = {
    "id": "apollo-demo", "title": "Project Apollo · Sprint Planning", "date": "2026-10-05", "duration": "34 min", "participants": 5,
    "summary": "The Apollo team aligned on a Friday beta deployment, with load testing and security approval as the final gates. Authentication ownership is clear, while data residency remains unresolved.",
    "decisions": [
        {"decision": "Use PostgreSQL for reporting", "speaker": "Priya Nair", "timestamp": "12:41", "confidence": .94, "evidence": "We should use PostgreSQL for reporting because the audit trail needs relational queries and predictable backups."},
        {"decision": "Beta deployment is Friday, conditional on gates", "speaker": "Maya Chen", "timestamp": "28:15", "confidence": .91, "evidence": "Decision: beta deployment is Friday, provided the load test and security review are green."},
        {"decision": "Hold a readiness review Wednesday", "speaker": "Maya Chen", "timestamp": "28:15", "confidence": .88, "evidence": "Let us reconvene Wednesday."},
    ],
    "actions": [
        {"task": "Finalize OAuth callback handling", "owner": "Priya Nair", "deadline": "Tomorrow", "priority": "High", "status": "In progress", "timestamp": "09:38"},
        {"task": "Publish the load-test report", "owner": "Marcus Taylor", "deadline": "Oct 08", "priority": "Medium", "status": "Pending", "timestamp": "18:42"},
        {"task": "Schedule security review", "owner": "Elena Rossi", "deadline": "Oct 10", "priority": "High", "status": "Blocked", "timestamp": "23:17"},
        {"task": "Update onboarding checklist", "owner": "Jordan Davis", "deadline": "Oct 12", "priority": "Low", "status": "Pending", "timestamp": "28:15"},
    ],
    "risks": [
        {"risk": "Security approval pending", "severity": "High", "timestamp": "23:17", "recommendation": "Schedule the review and confirm the compliance owner."},
        {"risk": "Data residency unresolved", "severity": "Medium", "timestamp": "31:04", "recommendation": "Add regional residency to the beta scope decision."},
    ],
}

def create_token(email: str) -> str:
    return jwt.encode({"sub": email, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, algorithm="HS256")

def current_user(token: str | None = None):
    if not token: return {"email": "demo@meetmind.ai"}
    try: return {"email": jwt.decode(token.removeprefix("Bearer "), SECRET, algorithms=["HS256"])["sub"]}
    except jwt.PyJWTError as exc: raise HTTPException(status_code=401, detail="Authentication expired") from exc

@app.get("/api/health")
def health(): return {"status": "ok", "service": "meetmind-api", "demo_mode": os.getenv("AI_PROVIDER", "demo") == "demo"}

@app.post("/api/auth/register", response_model=Token, status_code=201)
def register(credentials: UserCredentials):
    if credentials.email in USERS: raise HTTPException(409, "An account with this email already exists")
    USERS[credentials.email] = pwd.hash(credentials.password)
    return Token(access_token=create_token(credentials.email))

@app.post("/api/auth/login", response_model=Token)
def login(credentials: UserCredentials):
    if not pwd.verify(credentials.password, USERS.get(credentials.email, pwd.hash("invalid-password"))): raise HTTPException(401, "Invalid email or password")
    return Token(access_token=create_token(credentials.email))

@app.get("/api/meetings")
def meetings(): return {"items": [DEMO_MEETING], "total": 1}

@app.get("/api/meetings/{meeting_id}")
def meeting(meeting_id: str):
    if meeting_id != DEMO_MEETING["id"]: raise HTTPException(404, "Meeting not found")
    return DEMO_MEETING

@app.post("/api/meetings/{meeting_id}/upload")
async def upload(meeting_id: str, file: UploadFile = File(...)):
    allowed = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "video/mp4", "text/plain", "text/vtt"}
    if file.content_type not in allowed: raise HTTPException(415, "Unsupported meeting file type")
    content = await file.read()
    if len(content) > 250 * 1024 * 1024: raise HTTPException(413, "Meeting file exceeds the 250 MB limit")
    return {"filename": file.filename, "bytes": len(content), "status": "uploaded"}

@app.post("/api/meetings/{meeting_id}/ask")
def ask(meeting_id: str, question: Question):
    if meeting_id != DEMO_MEETING["id"]: raise HTTPException(404, "Meeting not found")
    q = question.question.lower()
    if any(word in q for word in ("deployment", "deploy", "friday")):
        return {"answer": "The beta deployment is planned for Friday, conditional on the load test and security review being green.", "confidence": .92, "evidence": [DEMO_MEETING["decisions"][1]]}
    if "risk" in q: return {"answer": "Two risks were raised: pending security approval and unresolved data residency scope.", "confidence": .89, "evidence": DEMO_MEETING["risks"]}
    return {"answer": "I couldn't find sufficient evidence in this meeting.", "confidence": .2, "evidence": []}

@app.get("/api/actions")
def actions(): return {"items": DEMO_MEETING["actions"], "total": len(DEMO_MEETING["actions"])}

@app.post("/api/meetings/{meeting_id}/process")
def process(meeting_id: str): return {"meeting_id": meeting_id, "status": "completed", "mode": os.getenv("AI_PROVIDER", "demo")}

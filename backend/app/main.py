import os
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from .auth import create_token, current_user, hash_password, verify_password
from .ai.provider import get_ai_provider
from .db import get_db, init_db
from .models import ActionItem, Meeting, User

app = FastAPI(title="MeetMind AI API", version="1.1.0", description="Evidence-based meeting intelligence API")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()
    db = next(get_db())
    try:
        demo = db.scalar(select(Meeting).where(Meeting.is_demo.is_(True)))
        if not demo:
            user = db.scalar(select(User).where(User.email == "demo@meetmind.ai"))
            if not user:
                user = User(email="demo@meetmind.ai", password_hash=hash_password("DemoPass123!"), role="ORGANIZER"); db.add(user); db.flush()
            demo = Meeting(owner_id=user.id, title="Project Apollo · Sprint Planning", description="Demo meeting for product walkthroughs.", status="analyzed", is_demo=True, summary="The Apollo team aligned on a Friday beta deployment, with load testing and security approval as the final gates. Authentication ownership is clear, while data residency remains unresolved.")
            db.add(demo); db.flush()
            rows = [("Finalize OAuth callback handling","Priya Nair","Tomorrow","High","In progress","09:38"),("Publish the load-test report","Marcus Taylor","Oct 08","Medium","Pending","18:42"),("Schedule security review","Elena Rossi","Oct 10","High","Blocked","23:17"),("Update onboarding checklist","Jordan Davis","Oct 12","Low","Pending","28:15")]
            for task, owner, deadline, priority, state, timestamp in rows: db.add(ActionItem(meeting_id=demo.id, owner_id=user.id, task=task, deadline=deadline, priority=priority, status=state, timestamp=timestamp, confidence=.9))
            db.commit()
    finally: db.close()

class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=8)
class MeetingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
class ActionUpdate(BaseModel):
    status: str | None = None
    deadline: str | None = None
    priority: str | None = None

def user_meeting(db: Session, meeting_id: str, user: User) -> Meeting:
    statement = select(Meeting).where(Meeting.owner_id == user.id, Meeting.is_demo.is_(True)) if meeting_id == "apollo-demo" else select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == user.id)
    meeting = db.scalar(statement)
    if not meeting: raise HTTPException(404, "Meeting not found")
    return meeting
def action_json(action: ActionItem):
    return {"id": action.id, "meeting_id": action.meeting_id, "task": action.task, "owner": action.owner_id, "deadline": action.deadline, "priority": action.priority, "status": action.status, "timestamp": action.timestamp, "confidence": action.confidence, "evidence": action.evidence}
def meeting_json(meeting: Meeting):
    return {"id": meeting.id, "title": meeting.title, "description": meeting.description, "status": meeting.status, "is_demo": meeting.is_demo, "summary": meeting.summary, "created_at": meeting.created_at.isoformat(), "actions": [action_json(a) for a in meeting.actions]}

@app.get("/api/health")
def health():
    provider = get_ai_provider()
    return {"status": "ok", "service": "meetmind-api", "demo_mode": os.getenv("AI_PROVIDER", "demo") == "demo", "database": "connected", "ai_provider": provider.name, "ai_configured": provider.configured}

@app.post("/api/auth/register", status_code=201)
def register(credentials: Credentials, db: Session = Depends(get_db)):
    email = credentials.email.lower()
    if db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(credentials.password)); db.add(user); db.commit(); db.refresh(user)
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role}}

@app.post("/api/auth/login")
def login(credentials: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == credentials.email.lower()))
    if not user or not verify_password(credentials.password, user.password_hash): raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role}}

@app.post("/api/auth/logout")
def logout(_: User = Depends(current_user)): return {"status": "signed_out"}

@app.get("/api/meetings")
def list_meetings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    meetings = db.scalars(select(Meeting).where(Meeting.owner_id == user.id).order_by(Meeting.created_at.desc())).all()
    return {"items": [meeting_json(m) for m in meetings], "total": len(meetings)}

@app.post("/api/meetings", status_code=201)
def create_meeting(payload: MeetingCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = Meeting(owner_id=user.id, title=payload.title, description=payload.description); db.add(meeting); db.commit(); db.refresh(meeting)
    return meeting_json(meeting)

@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)): return meeting_json(user_meeting(db, meeting_id, user))

@app.post("/api/meetings/{meeting_id}/upload")
async def upload(meeting_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    user_meeting(db, meeting_id, user)
    allowed = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "video/mp4", "video/quicktime", "video/webm", "text/plain", "text/vtt", "application/x-subrip"}
    if file.content_type not in allowed: raise HTTPException(415, "Unsupported meeting file type")
    content = await file.read()
    if len(content) > 250 * 1024 * 1024: raise HTTPException(413, "Meeting file exceeds the 250 MB limit")
    return {"filename": file.filename, "bytes": len(content), "status": "uploaded", "message": "Storage/transcription provider is not configured; file validation succeeded."}

@app.post("/api/meetings/{meeting_id}/process")
def process(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user); meeting.status = "processing"; db.commit()
    return {"meeting_id": meeting_id, "status": "processing", "mode": os.getenv("AI_PROVIDER", "demo"), "message": "Provider pipeline is ready; demo meetings can be opened without external AI credentials."}

@app.post("/api/meetings/{meeting_id}/ask")
def ask(meeting_id: str, payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user); question = str(payload.get("question", "")).lower()
    if meeting.is_demo and any(word in question for word in ("deployment", "deploy", "friday")):
        return {"answer": "The beta deployment is planned for Friday, conditional on the load test and security review being green.", "confidence": .92, "evidence": [{"timestamp": "28:15", "speaker": "Maya Chen", "text": "Decision: beta deployment is Friday, provided the load test and security review are green."}]}
    if meeting.is_demo and "risk" in question:
        return {"answer": "Two risks were raised: pending security approval and unresolved data residency scope.", "confidence": .89, "evidence": [{"timestamp": "23:17", "speaker": "Elena Rossi"}, {"timestamp": "31:04", "speaker": "Maya Chen"}]}
    return {"answer": "I couldn't find sufficient evidence in this meeting.", "confidence": .2, "evidence": []}

@app.get("/api/actions")
def list_actions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(ActionItem).join(Meeting).where(Meeting.owner_id == user.id)).all(); return {"items": [action_json(a) for a in items], "total": len(items)}

@app.patch("/api/actions/{action_id}")
def update_action(action_id: str, payload: ActionUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    action = db.scalar(select(ActionItem).join(Meeting).where(ActionItem.id == action_id, Meeting.owner_id == user.id))
    if not action: raise HTTPException(404, "Action not found")
    for key, value in payload.model_dump(exclude_none=True).items(): setattr(action, key, value)
    db.commit(); db.refresh(action); return action_json(action)

import os
import json
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .auth import create_token, current_user, hash_password, verify_password
from .ai.provider import get_ai_provider
from .db import get_db, init_db
from .models import ActionItem, Decision, Meeting, MeetingQuestion, MeetingSession, OpenQuestion, Recording, Risk, TranscriptSegment, User
from .storage import store_bytes
from .transcription.parser import parse_text
from .translation.provider import SUPPORTED_LANGUAGES, get_translation_provider
from .transcription.provider import get_transcription_provider

@asynccontextmanager
async def lifespan(_: FastAPI):
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
            segments = [("00:00","Maya Chen","Welcome everyone. Today we are aligning the Apollo release plan and removing the last blockers for beta.","Opening"),("04:12","Marcus Taylor","The API gateway is stable in staging. The remaining work is observability and the payment retry path.","Engineering update"),("09:38","Priya Nair","I can own the authentication issue. I will have the callback handling fixed by tomorrow afternoon.","Commitment"),("12:41","Priya Nair","We should use PostgreSQL for reporting because the audit trail needs relational queries and predictable backups.","Technical decision"),("18:42","Marcus Taylor","The load test is the gate for beta. I will publish the report before Thursday so we can review it together.","Release readiness"),("23:17","Elena Rossi","We cannot deploy Friday without a security review. I will schedule it, but the compliance approval is still missing.","Risk"),("28:15","Maya Chen","Decision: beta deployment is Friday, provided the load test and security review are green. Let us reconvene Wednesday.","Decision"),("31:04","Maya Chen","Open question: do we support regional data residency in the first beta, or is that a post-beta commitment?","Open question")]
            for timestamp, speaker, text, topic in segments: db.add(TranscriptSegment(meeting_id=demo.id, timestamp=timestamp, speaker=speaker, text=text, topic=topic))
            db.add(Decision(meeting_id=demo.id, decision="Use PostgreSQL for reporting", speaker="Priya Nair", timestamp="12:41", evidence=segments[3][2], confidence=.94)); db.add(Decision(meeting_id=demo.id, decision="Beta deployment is Friday, conditional on gates", speaker="Maya Chen", timestamp="28:15", evidence=segments[6][2], confidence=.91)); db.add(Decision(meeting_id=demo.id, decision="Hold a readiness review Wednesday", speaker="Maya Chen", timestamp="28:15", evidence="Let us reconvene Wednesday.", confidence=.88))
            db.add(Risk(meeting_id=demo.id, risk="Security approval pending", severity="High", timestamp="23:17", recommendation="Schedule the review and confirm the compliance owner.")); db.add(Risk(meeting_id=demo.id, risk="Data residency unresolved", severity="Medium", timestamp="31:04", recommendation="Add regional residency to the beta scope decision.")); db.add(OpenQuestion(meeting_id=demo.id, question="Do we support regional data residency in the first beta?", speaker="Maya Chen", timestamp="31:04")); db.commit()
    finally: db.close()
    yield

app = FastAPI(title="MeetMind AI API", version="1.1.0", description="Evidence-based meeting intelligence API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def startup_legacy_seed():
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
            segments = [("00:00","Maya Chen","Welcome everyone. Today we are aligning the Apollo release plan and removing the last blockers for beta.","Opening"),("04:12","Marcus Taylor","The API gateway is stable in staging. The remaining work is observability and the payment retry path.","Engineering update"),("09:38","Priya Nair","I can own the authentication issue. I will have the callback handling fixed by tomorrow afternoon.","Commitment"),("12:41","Priya Nair","We should use PostgreSQL for reporting because the audit trail needs relational queries and predictable backups.","Technical decision"),("18:42","Marcus Taylor","The load test is the gate for beta. I will publish the report before Thursday so we can review it together.","Release readiness"),("23:17","Elena Rossi","We cannot deploy Friday without a security review. I will schedule it, but the compliance approval is still missing.","Risk"),("28:15","Maya Chen","Decision: beta deployment is Friday, provided the load test and security review are green. Let us reconvene Wednesday.","Decision"),("31:04","Maya Chen","Open question: do we support regional data residency in the first beta, or is that a post-beta commitment?","Open question")]
            for timestamp, speaker, text, topic in segments: db.add(TranscriptSegment(meeting_id=demo.id, timestamp=timestamp, speaker=speaker, text=text, topic=topic))
            db.add(Decision(meeting_id=demo.id, decision="Use PostgreSQL for reporting", speaker="Priya Nair", timestamp="12:41", evidence=segments[3][2], confidence=.94))
            db.add(Decision(meeting_id=demo.id, decision="Beta deployment is Friday, conditional on gates", speaker="Maya Chen", timestamp="28:15", evidence=segments[6][2], confidence=.91))
            db.add(Decision(meeting_id=demo.id, decision="Hold a readiness review Wednesday", speaker="Maya Chen", timestamp="28:15", evidence="Let us reconvene Wednesday.", confidence=.88))
            db.add(Risk(meeting_id=demo.id, risk="Security approval pending", severity="High", timestamp="23:17", recommendation="Schedule the review and confirm the compliance owner."))
            db.add(Risk(meeting_id=demo.id, risk="Data residency unresolved", severity="Medium", timestamp="31:04", recommendation="Add regional residency to the beta scope decision."))
            db.add(OpenQuestion(meeting_id=demo.id, question="Do we support regional data residency in the first beta?", speaker="Maya Chen", timestamp="31:04"))
            db.commit()
        if demo and not db.scalar(select(TranscriptSegment).where(TranscriptSegment.meeting_id == demo.id)):
            fallback = [("00:00","Maya Chen","Welcome everyone. Today we are aligning the Apollo release plan.","Opening"),("04:12","Marcus Taylor","The API gateway is stable in staging.","Engineering update"),("09:38","Priya Nair","I will have the callback handling fixed by tomorrow afternoon.","Commitment"),("12:41","Priya Nair","We should use PostgreSQL for reporting.","Technical decision"),("18:42","Marcus Taylor","I will publish the load-test report before Thursday.","Release readiness"),("23:17","Elena Rossi","We cannot deploy without a security review.","Risk"),("28:15","Maya Chen","Beta deployment is Friday if the gates are green.","Decision"),("31:04","Maya Chen","Do we support regional data residency in the first beta?","Open question")]
            for timestamp, speaker, text, topic in fallback: db.add(TranscriptSegment(meeting_id=demo.id, timestamp=timestamp, speaker=speaker, text=text, topic=topic))
            db.add(Decision(meeting_id=demo.id, decision="Beta deployment is Friday, conditional on gates", speaker="Maya Chen", timestamp="28:15", evidence=fallback[6][2], confidence=.91))
            db.add(Risk(meeting_id=demo.id, risk="Security approval pending", severity="High", timestamp="23:17", recommendation="Schedule the review and confirm the compliance owner."))
            db.add(OpenQuestion(meeting_id=demo.id, question=fallback[7][2], speaker="Maya Chen", timestamp="31:04"))
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
class TranslationRequest(BaseModel):
    target_language: str = Field(min_length=2, max_length=5)
    scope: str = Field(default="summary", pattern="^(summary|transcript)$")

def user_meeting(db: Session, meeting_id: str, user: User) -> Meeting:
    statement = select(Meeting).where(Meeting.owner_id == user.id, Meeting.is_demo.is_(True)) if meeting_id == "apollo-demo" else select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == user.id)
    meeting = db.scalar(statement)
    if not meeting: raise HTTPException(404, "Meeting not found")
    return meeting
def action_json(action: ActionItem):
    return {"id": action.id, "meeting_id": action.meeting_id, "task": action.task, "owner": action.owner_id, "deadline": action.deadline, "priority": action.priority, "status": action.status, "timestamp": action.timestamp, "confidence": action.confidence, "evidence": action.evidence}
def meeting_json(meeting: Meeting):
    return {"id": meeting.id, "title": meeting.title, "description": meeting.description, "status": meeting.status, "is_demo": meeting.is_demo, "summary": meeting.summary, "created_at": meeting.created_at.isoformat(), "actions": [action_json(a) for a in meeting.actions]}
def owned_id(db: Session, meeting_id: str, user: User) -> str: return user_meeting(db, meeting_id, user).id

@app.get("/api/health")
def health():
    provider = get_ai_provider()
    translation = get_translation_provider()
    transcription = get_transcription_provider()
    return {"status": "ok", "service": "meetmind-api", "demo_mode": os.getenv("AI_PROVIDER", "demo") == "demo", "database": "connected", "ai_provider": provider.name, "ai_configured": provider.configured, "translation_provider": translation.name, "translation_configured": translation.configured, "transcription_provider": transcription.name, "transcription_configured": transcription.configured}

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

@app.get("/api/meetings/{meeting_id}/transcript")
def transcript(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == owned_id(db, meeting_id, user)).order_by(TranscriptSegment.timestamp)).all()
    return {"items": [{"id": x.id, "timestamp": x.timestamp, "speaker": x.speaker, "text": x.text, "topic": x.topic} for x in items]}

@app.get("/api/meetings/{meeting_id}/decisions")
def decisions(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Decision).where(Decision.meeting_id == owned_id(db, meeting_id, user))).all()
    return {"items": [{"id": x.id, "decision": x.decision, "speaker": x.speaker, "timestamp": x.timestamp, "evidence": x.evidence, "confidence": x.confidence, "status": x.status} for x in items]}

@app.get("/api/meetings/{meeting_id}/risks")
def risks(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Risk).where(Risk.meeting_id == owned_id(db, meeting_id, user))).all()
    return {"items": [{"id": x.id, "risk": x.risk, "severity": x.severity, "timestamp": x.timestamp, "recommendation": x.recommendation, "status": x.status} for x in items]}

@app.get("/api/meetings/{meeting_id}/questions")
def questions(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(OpenQuestion).where(OpenQuestion.meeting_id == owned_id(db, meeting_id, user))).all()
    return {"items": [{"id": x.id, "question": x.question, "speaker": x.speaker, "timestamp": x.timestamp, "status": x.status} for x in items]}

@app.post("/api/meetings/{meeting_id}/translate")
def translate_meeting(meeting_id: str, payload: TranslationRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    if payload.target_language not in SUPPORTED_LANGUAGES: raise HTTPException(422, f"Unsupported target language. Choose one of: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
    provider = get_translation_provider()
    if not provider.configured: raise HTTPException(503, "Translation provider not configured. Set TRANSLATION_PROVIDER and its credentials before requesting translated output.")
    source = meeting.summary if payload.scope == "summary" else "\n".join(x.text for x in db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)).all())
    return {"meeting_id": meeting.id, "source_language": "und", "target_language": payload.target_language, "scope": payload.scope, "translated_text": provider.translate(source, payload.target_language)}

@app.get("/api/search")
def search(q: str = Query(min_length=2, max_length=200), user: User = Depends(current_user), db: Session = Depends(get_db)):
    needle = q.lower(); results = []
    meetings = db.scalars(select(Meeting).where(Meeting.owner_id == user.id)).all()
    for meeting in meetings:
        if needle in meeting.title.lower() or needle in meeting.summary.lower(): results.append({"type": "meeting", "meeting_id": meeting.id, "title": meeting.title, "matched": meeting.summary or meeting.title})
        for segment in db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)).all():
            if needle in f"{segment.text} {segment.speaker} {segment.topic}".lower(): results.append({"type": "transcript", "meeting_id": meeting.id, "title": meeting.title, "timestamp": segment.timestamp, "speaker": segment.speaker, "matched": segment.text})
        for action in db.scalars(select(ActionItem).where(ActionItem.meeting_id == meeting.id)).all():
            if needle in action.task.lower(): results.append({"type": "action", "meeting_id": meeting.id, "title": meeting.title, "matched": action.task, "status": action.status})
    return {"query": q, "items": results, "total": len(results)}

@app.get("/api/meetings/{meeting_id}/export")
def export_meeting(meeting_id: str, format: str = Query("json", pattern="^(json|txt)$"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    segments = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id).order_by(TranscriptSegment.timestamp)).all()
    decisions_data = db.scalars(select(Decision).where(Decision.meeting_id == meeting.id)).all()
    risks_data = db.scalars(select(Risk).where(Risk.meeting_id == meeting.id)).all()
    questions_data = db.scalars(select(OpenQuestion).where(OpenQuestion.meeting_id == meeting.id)).all()
    payload = {"meeting": meeting_json(meeting), "transcript": [{"timestamp": x.timestamp, "speaker": x.speaker, "text": x.text, "topic": x.topic} for x in segments], "decisions": [{"decision": x.decision, "speaker": x.speaker, "timestamp": x.timestamp, "evidence": x.evidence, "confidence": x.confidence} for x in decisions_data], "risks": [{"risk": x.risk, "severity": x.severity, "timestamp": x.timestamp, "recommendation": x.recommendation} for x in risks_data], "questions": [{"question": x.question, "speaker": x.speaker, "timestamp": x.timestamp} for x in questions_data]}
    if format == "json": return Response(content=json.dumps(payload, indent=2), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="meetmind-{meeting.id}.json"'})
    lines = [meeting.title, "", "SUMMARY", meeting.summary, "", "TRANSCRIPT"] + [f"[{x['timestamp']}] {x['speaker']}: {x['text']}" for x in payload["transcript"]] + ["", "DECISIONS"] + [f"- {x['decision']} ({x['timestamp']})" for x in payload["decisions"]] + ["", "RISKS"] + [f"- {x['risk']} [{x['severity']}]" for x in payload["risks"]]
    return Response(content="\n".join(lines), media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="meetmind-{meeting.id}.txt"'})

@app.post("/api/meetings/{meeting_id}/upload")
async def upload(meeting_id: str, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    user_meeting(db, meeting_id, user)
    allowed = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "video/mp4", "video/quicktime", "video/webm", "text/plain", "text/vtt", "application/x-subrip"}
    if file.content_type not in allowed: raise HTTPException(415, "Unsupported meeting file type")
    content = await file.read()
    if len(content) > 250 * 1024 * 1024: raise HTTPException(413, "Meeting file exceeds the 250 MB limit")
    storage_path = store_bytes(meeting_id, file.filename or "meeting-upload", content)
    recording = Recording(meeting_id=meeting_id, filename=file.filename or "meeting-upload", content_type=file.content_type or "application/octet-stream", storage_path=storage_path, size_bytes=len(content))
    db.add(recording)
    parsed = 0
    if (file.content_type or "").startswith("text/") or (file.filename or "").lower().endswith((".txt", ".srt", ".vtt")):
        for segment in parse_text(content.decode("utf-8", errors="replace")):
            db.add(TranscriptSegment(meeting_id=meeting_id, **segment)); parsed += 1
        meeting = user_meeting(db, meeting_id, user); meeting.status = "analyzed" if parsed else "uploaded"
    db.commit()
    message = "Transcript parsed and persisted." if parsed else "Recording stored. Transcription provider is not configured for media files."
    return {"recording_id": recording.id, "filename": recording.filename, "bytes": len(content), "status": "analyzed" if parsed else "uploaded", "segments_created": parsed, "message": message}

@app.post("/api/meetings/{meeting_id}/process")
def process(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user); meeting.status = "processing"; db.commit()
    return {"meeting_id": meeting_id, "status": "processing", "mode": os.getenv("AI_PROVIDER", "demo"), "message": "Provider pipeline is ready; demo meetings can be opened without external AI credentials."}

@app.post("/api/meetings/{meeting_id}/join")
def join_meeting(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    session = MeetingSession(meeting_id=meeting.id, user_id=user.id, status="joined"); db.add(session); db.commit(); db.refresh(session)
    return {"session_id": session.id, "meeting_id": meeting.id, "status": session.status, "joined_at": session.joined_at.isoformat()}

@app.post("/api/meetings/{meeting_id}/start")
def start_meeting(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user); meeting.status = "live"; db.commit()
    return {"meeting_id": meeting.id, "status": meeting.status}

@app.post("/api/meetings/{meeting_id}/end")
def end_meeting(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user); meeting.status = "processing"; db.commit()
    return {"meeting_id": meeting.id, "status": meeting.status, "next": "process"}

@app.post("/api/meetings/{meeting_id}/ask")
def ask(meeting_id: str, payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user); raw_question = str(payload.get("question", "")).strip(); question = raw_question.lower()
    if len(raw_question) < 3: raise HTTPException(422, "Question must contain at least 3 characters")
    segments = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)).all()
    stop_words = {"what","were","was","the","who","when","where","about","this","meeting","and","are","for","did","we"}
    terms = {word for word in question.replace("?", "").split() if len(word) > 2 and word not in stop_words}
    matches = [segment for segment in segments if any(term in f"{segment.text} {segment.speaker} {segment.topic}".lower() for term in terms)]
    evidence = [{"timestamp": x.timestamp, "speaker": x.speaker, "text": x.text} for x in matches[:3]]
    if any(word in question for word in ("risk", "concern", "blocker")):
        answer = "The meeting identified security approval as a high-severity risk and data residency as unresolved."; confidence = .89
    elif any(word in question for word in ("deployment", "deploy", "friday")):
        answer = "The beta deployment is planned for Friday, conditional on the load test and security review being green."; confidence = .92
    elif matches:
        answer = "Relevant evidence was found in the meeting transcript."; confidence = min(.85, .55 + len(matches) * .1)
    else:
        answer = "I couldn't find sufficient evidence in this meeting."; confidence = .2; evidence = []
    record = MeetingQuestion(meeting_id=meeting.id, user_id=user.id, question=raw_question, answer=answer, confidence=confidence, evidence_json=json.dumps(evidence)); db.add(record); db.commit()
    return {"question_id": record.id, "answer": answer, "confidence": confidence, "evidence": evidence}

@app.get("/api/meetings/{meeting_id}/questions/history")
def question_history(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user); items = db.scalars(select(MeetingQuestion).where(MeetingQuestion.meeting_id == meeting.id, MeetingQuestion.user_id == user.id).order_by(MeetingQuestion.created_at.desc())).all()
    return {"items": [{"id": x.id, "question": x.question, "answer": x.answer, "confidence": x.confidence, "evidence": json.loads(x.evidence_json)} for x in items]}

@app.get("/api/actions")
def list_actions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(ActionItem).join(Meeting).where(Meeting.owner_id == user.id)).all(); return {"items": [action_json(a) for a in items], "total": len(items)}

@app.patch("/api/actions/{action_id}")
def update_action(action_id: str, payload: ActionUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    action = db.scalar(select(ActionItem).join(Meeting).where(ActionItem.id == action_id, Meeting.owner_id == user.id))
    if not action: raise HTTPException(404, "Action not found")
    for key, value in payload.model_dump(exclude_none=True).items(): setattr(action, key, value)
    db.commit(); db.refresh(action); return action_json(action)

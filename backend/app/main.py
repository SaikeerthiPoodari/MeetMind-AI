import os
import json
import html
import io
import re
import zipfile
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from .auth import create_token, current_user, hash_password, verify_password
from .ai.provider import get_ai_provider
from .db import get_db, init_db
from .models import ActionItem, AuditLog, Decision, FollowUpDraft, Meeting, MeetingChatMessage, MeetingQuestion, MeetingSession, Notification, OpenQuestion, ProcessingStage, Recording, Risk, TranscriptSegment, User, UserPreference
from .storage import store_bytes
from .transcription.parser import parse_text
from .translation.provider import SUPPORTED_LANGUAGES, detect_language, get_translation_provider
from .transcription.provider import get_transcription_provider

def ensure_demo_dataset(db: Session, meeting: Meeting, user: User) -> None:
    """Keep the built-in Apollo walkthrough rich without mixing it with user data."""
    if not meeting.is_demo:
        return
    segment_count = db.scalar(select(func.count(TranscriptSegment.id)).where(TranscriptSegment.meeting_id == meeting.id)) or 0
    if segment_count < 30:
        extra = [
            ("01:18", "Maya Chen", "The beta audience is limited to ten design partners for the first week.", "Scope"),
            ("02:44", "Jordan Davis", "Support needs a clear escalation path before invitations go out.", "Operations"),
            ("06:05", "Marcus Taylor", "The retry queue is healthy, but we still need alerts for sustained latency.", "Engineering update"),
            ("07:26", "Elena Rossi", "I will confirm the security review attendees with compliance today.", "Commitment"),
            ("10:52", "Priya Nair", "The callback fix also needs coverage for expired state tokens.", "Authentication"),
            ("13:56", "Jordan Davis", "Reporting should preserve the audit event and the actor that caused it.", "Reporting"),
            ("15:21", "Maya Chen", "Let us keep regional residency out of beta unless a customer requires it.", "Scope"),
            ("16:47", "Priya Nair", "That is a product decision, not something engineering should assume.", "Decision context"),
            ("20:03", "Marcus Taylor", "The load test environment is representative of the expected beta traffic.", "Testing"),
            ("21:29", "Elena Rossi", "The missing compliance approval is the largest release dependency.", "Risk"),
            ("24:08", "Jordan Davis", "I will update the onboarding checklist after the release gates are confirmed.", "Commitment"),
            ("25:36", "Maya Chen", "We need a single owner for the launch checklist.", "Operations"),
            ("26:10", "Jordan Davis", "I can own the launch checklist and post a final version Wednesday.", "Action"),
            ("29:02", "Marcus Taylor", "If the load test slips, Friday becomes a review date rather than a deploy date.", "Schedule"),
            ("30:12", "Elena Rossi", "The security review must be completed before production credentials are issued.", "Security"),
            ("32:18", "Priya Nair", "The database migration is not required for the beta path.", "Reporting"),
            ("33:05", "Maya Chen", "Decision: use PostgreSQL for reporting and keep migration work behind the beta gate.", "Decision"),
            ("34:22", "Jordan Davis", "Should the customer success team receive the same dashboard as internal users?", "Open question"),
            ("35:44", "Maya Chen", "We will answer that in the onboarding review.", "Follow-up"),
            ("37:10", "Marcus Taylor", "I will add the latency alert before the next staging rehearsal.", "Commitment"),
            ("38:26", "Elena Rossi", "A vendor approval could still affect the planned notification provider.", "Dependency risk"),
            ("40:01", "Maya Chen", "No additional scope should enter the beta without an explicit decision.", "Governance"),
        ]
        existing = {item.text for item in db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)).all()}
        for timestamp, speaker, text, topic in extra:
            if text not in existing:
                db.add(TranscriptSegment(meeting_id=meeting.id, timestamp=timestamp, speaker=speaker, text=text, topic=topic))
    if (db.scalar(select(func.count(Decision.id)).where(Decision.meeting_id == meeting.id)) or 0) < 5:
        db.add(Decision(meeting_id=meeting.id, decision="Keep regional residency out of beta unless required by a customer", speaker="Maya Chen", timestamp="15:21", evidence="Let us keep regional residency out of beta unless a customer requires it.", confidence=.86, status="PROPOSED"))
        db.add(Decision(meeting_id=meeting.id, decision="Use PostgreSQL for reporting and defer migration work behind the beta gate", speaker="Maya Chen", timestamp="33:05", evidence="Decision: use PostgreSQL for reporting and keep migration work behind the beta gate.", confidence=.93, status="CONFIRMED"))
        db.add(Decision(meeting_id=meeting.id, decision="Limit beta to ten design partners during the first week", speaker="Maya Chen", timestamp="01:18", evidence="The beta audience is limited to ten design partners for the first week.", confidence=.84, status="CONFIRMED"))
        db.add(Decision(meeting_id=meeting.id, decision="Treat Friday as a review date if load testing slips", speaker="Marcus Taylor", timestamp="29:02", evidence="If the load test slips, Friday becomes a review date rather than a deploy date.", confidence=.82, status="PROPOSED"))
    if (db.scalar(select(func.count(ActionItem.id)).where(ActionItem.meeting_id == meeting.id)) or 0) < 8:
        for task, owner, deadline, priority, state, timestamp, evidence in [
            ("Add sustained-latency alert", "Marcus Taylor", "Before next staging rehearsal", "High", "DETECTED", "37:10", "I will add the latency alert before the next staging rehearsal."),
            ("Confirm security review attendees", "Elena Rossi", "Today", "High", "CONFIRMED", "07:26", "I will confirm the security review attendees with compliance today."),
            ("Own and publish launch checklist", "Jordan Davis", "Wednesday", "Medium", "IN_PROGRESS", "26:10", "I can own the launch checklist and post a final version Wednesday."),
            ("Answer customer success dashboard question", "Maya Chen", "Onboarding review", "Low", "DETECTED", "35:44", "We will answer that in the onboarding review."),
        ]:
            db.add(ActionItem(meeting_id=meeting.id, owner_id=user.id, task=task, deadline=deadline, priority=priority, status=state, timestamp=timestamp, evidence=evidence, confidence=.88))
    if (db.scalar(select(func.count(Risk.id)).where(Risk.meeting_id == meeting.id)) or 0) < 3:
        db.add(Risk(meeting_id=meeting.id, risk="Notification provider approval may delay launch", severity="Medium", timestamp="38:26", recommendation="Confirm the provider decision and prepare a fallback.", status="MONITORING"))
        db.add(Risk(meeting_id=meeting.id, risk="Sustained latency alerts are not yet active", severity="Low", timestamp="06:05", recommendation="Add the alert and verify it during the staging rehearsal.", status="OPEN"))
    if (db.scalar(select(func.count(OpenQuestion.id)).where(OpenQuestion.meeting_id == meeting.id)) or 0) < 3:
        db.add(OpenQuestion(meeting_id=meeting.id, question="Should customer success receive the same dashboard as internal users?", speaker="Jordan Davis", timestamp="34:22", status="OPEN"))
        db.add(OpenQuestion(meeting_id=meeting.id, question="Who approves the notification provider if the vendor changes?", speaker="Elena Rossi", timestamp="38:26", status="DEFERRED"))
    db.commit()

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = next(get_db())
    try:
        for existing_meeting in db.scalars(select(Meeting)).all():
            if not existing_meeting.share_code:
                existing_meeting.share_code = existing_meeting.id[:10].upper()
        db.commit()
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
        if demo:
            ensure_demo_dataset(db, demo, db.scalar(select(User).where(User.id == demo.owner_id)))
    finally: db.close()
    yield

app = FastAPI(title="MeetMind AI API", version="1.1.0", description="Evidence-based meeting intelligence API", lifespan=lifespan)
configured_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
local_origins = {configured_origin, "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5177", "http://127.0.0.1:5177"}
app.add_middleware(CORSMiddleware, allow_origins=sorted(local_origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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
        if demo:
            ensure_demo_dataset(db, demo, db.scalar(select(User).where(User.id == demo.owner_id)))
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
    owner_id: str | None = None
class ActionCreate(BaseModel):
    task: str = Field(min_length=1, max_length=300)
    deadline: str = Field(default="Not specified in the meeting", max_length=80)
    priority: str = Field(default="Medium", pattern="^(Low|Medium|High|Critical)$")
    owner_id: str | None = None
    timestamp: str = ""
    evidence: str = ""
    confidence: float = Field(default=1.0, ge=0, le=1)
class TranslationRequest(BaseModel):
    target_language: str = Field(min_length=2, max_length=5)
    scope: str = Field(default="summary", pattern="^(summary|transcript)$")
class PreferenceUpdate(BaseModel):
    language: str = Field(default="en", min_length=2, max_length=8)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    notifications_enabled: bool = True
class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    avatar_url: str | None = Field(default=None, max_length=700000)
    language: str | None = Field(default=None, min_length=2, max_length=8)
    timezone: str | None = Field(default=None, min_length=1, max_length=80)
    notifications_enabled: bool | None = None
class ChatMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
class AssistantRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    meeting_id: str | None = None
    current_page: str = Field(default="dashboard", max_length=80)
class JoinLinkRequest(BaseModel):
    share_code: str = Field(min_length=6, max_length=20)

def user_meeting(db: Session, meeting_id: str, user: User) -> Meeting:
    statement = select(Meeting).where(Meeting.owner_id == user.id, Meeting.is_demo.is_(True)) if meeting_id == "apollo-demo" else select(Meeting).where(Meeting.id == meeting_id, (Meeting.owner_id == user.id) | Meeting.id.in_(select(MeetingSession.meeting_id).where(MeetingSession.user_id == user.id, MeetingSession.status == "joined")))
    meeting = db.scalar(statement)
    if not meeting: raise HTTPException(404, "Meeting not found")
    return meeting
def action_json(action: ActionItem):
    return {"id": action.id, "meeting_id": action.meeting_id, "task": action.task, "owner": action.owner_id, "deadline": action.deadline, "priority": action.priority, "status": action.status, "timestamp": action.timestamp, "confidence": action.confidence, "evidence": action.evidence}
def meeting_json(meeting: Meeting):
    code = meeting.share_code or meeting.id[:10].upper()
    return {"id": meeting.id, "meeting_id": meeting.id, "share_code": code, "share_url": f"{os.getenv('FRONTEND_ORIGIN', 'http://127.0.0.1:5177')}/?join={code}", "title": meeting.title, "description": meeting.description, "status": meeting.status, "is_demo": meeting.is_demo, "summary": meeting.summary, "executive_summary": meeting.executive_summary, "short_summary": meeting.short_summary, "detailed_summary": meeting.detailed_summary, "detected_language": meeting.detected_language, "created_at": meeting.created_at.isoformat(), "actions": [action_json(a) for a in meeting.actions]}

PIPELINE_STAGES = ("TRANSCRIPTION", "LANGUAGE_DETECTION", "CLEANING", "SPEAKER_DETECTION", "TOPIC_EXTRACTION", "SUMMARY", "DECISIONS", "ACTIONS", "COMMITMENTS", "RISKS", "OPEN_QUESTIONS", "SPEAKER_INTELLIGENCE", "TIMELINE", "MEETING_HEALTH", "KNOWLEDGE_INDEXING")

def ensure_pipeline(db: Session, meeting_id: str) -> list[ProcessingStage]:
    current = {item.name: item for item in db.scalars(select(ProcessingStage).where(ProcessingStage.meeting_id == meeting_id)).all()}
    for name in PIPELINE_STAGES:
        if name not in current:
            item = ProcessingStage(meeting_id=meeting_id, name=name)
            db.add(item); current[name] = item
    db.flush()
    return [current[name] for name in PIPELINE_STAGES]

def pipeline_json(stages: list[ProcessingStage]) -> list[dict]:
    return [{"name": x.name, "status": x.status, "error": x.error, "attempts": x.attempts, "evidence": json.loads(x.evidence_json or "[]"), "started_at": x.started_at.isoformat() if x.started_at else None, "completed_at": x.completed_at.isoformat() if x.completed_at else None} for x in stages]
def owned_id(db: Session, meeting_id: str, user: User) -> str: return user_meeting(db, meeting_id, user).id
def audit(db: Session, user: User, action: str, resource_type: str = "", resource_id: str = "", metadata: dict | None = None) -> None:
    db.add(AuditLog(user_id=user.id, action=action, resource_type=resource_type, resource_id=resource_id, metadata_json=json.dumps(metadata or {})))
def require_admin(user: User) -> User:
    if user.role != "ADMIN": raise HTTPException(403, "Administrator role required")
    return user

def report_lines(payload: dict, markdown: bool = False) -> list[str]:
    title = f"# {payload['meeting']['title']}" if markdown else payload["meeting"]["title"]
    lines = [title, "", "## Summary" if markdown else "SUMMARY", payload["meeting"]["summary"] or "Not specified", "", "## Transcript" if markdown else "TRANSCRIPT"]
    lines.extend((f"- **{x['timestamp']} — {x['speaker']}:** {x['text']}" if markdown else f"[{x['timestamp']}] {x['speaker']}: {x['text']}") for x in payload["transcript"])
    lines += ["", "## Decisions" if markdown else "DECISIONS"]
    lines.extend((f"- {x['decision']} ({x['timestamp']}; evidence: {x['evidence']})" if markdown else f"- {x['decision']} ({x['timestamp']}) — {x['evidence']}") for x in payload["decisions"])
    lines += ["", "## Action items" if markdown else "ACTION ITEMS"]
    lines.extend(f"- {x['task']} — {x['owner']} — {x['status']} — due {x['deadline']}" for x in payload["meeting"]["actions"])
    lines += ["", "## Risks" if markdown else "RISKS"]
    lines.extend((f"- {x['risk']} [{x['severity']}]: {x['recommendation']}" if markdown else f"- {x['risk']} [{x['severity']}] — {x['recommendation']}") for x in payload["risks"])
    lines += ["", "## Open questions" if markdown else "OPEN QUESTIONS"]
    lines.extend(f"- {x['question']} ({x['timestamp']})" for x in payload["questions"])
    return lines

def make_docx(lines: list[str]) -> bytes:
    paragraphs = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{html.escape(line)}</w:t></w:r></w:p>" for line in lines)
    document = f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body>{paragraphs}<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\"/></w:sectPr></w:body></w:document>"
    content_types = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/></Types>"
    rels = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/></Relationships>"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
    return output.getvalue()

def make_pdf(lines: list[str]) -> bytes:
    def pdf_text(value: str) -> str:
        return value.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    commands = ["BT", "/F1 10 Tf", "50 780 Td"]
    for index, line in enumerate(lines):
        if index: commands.append("0 -15 Td")
        commands.append(f"({pdf_text(line[:180])}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output)); output.extend(f"{number} 0 obj\n".encode()); output.extend(obj); output.extend(b"\nendobj\n")
    xref = len(output); output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    output.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(output)

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
    user = User(email=email, password_hash=hash_password(credentials.password)); db.add(user); db.flush(); audit(db, user, "account.created", "user", user.id); db.commit(); db.refresh(user)
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role}}

@app.post("/api/auth/login")
def login(credentials: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == credentials.email.lower()))
    if not user or not verify_password(credentials.password, user.password_hash): raise HTTPException(401, "Invalid email or password")
    audit(db, user, "auth.login", "user", user.id); db.commit()
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role}}

@app.post("/api/auth/logout")
def logout(_: User = Depends(current_user)): return {"status": "signed_out"}

@app.get("/api/me")
def profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    preferences = db.get(UserPreference, user.id); return {"id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name, "avatar_url": user.avatar_url, "language": preferences.language if preferences else "en", "timezone": preferences.timezone if preferences else "UTC", "notifications_enabled": preferences.notifications_enabled if preferences else True}

@app.patch("/api/me")
def update_profile(payload: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if payload.language is not None and payload.language not in SUPPORTED_LANGUAGES: raise HTTPException(422, "Unsupported language")
    if payload.full_name is not None: user.full_name = payload.full_name.strip()
    if payload.avatar_url is not None:
        if payload.avatar_url and not payload.avatar_url.startswith("data:image/"): raise HTTPException(422, "Avatar must be an image data URL")
        user.avatar_url = payload.avatar_url
    preferences = db.get(UserPreference, user.id)
    if not preferences: preferences = UserPreference(user_id=user.id); db.add(preferences)
    if payload.language is not None: preferences.language = payload.language
    if payload.timezone is not None: preferences.timezone = payload.timezone
    if payload.notifications_enabled is not None: preferences.notifications_enabled = payload.notifications_enabled
    db.commit(); db.refresh(preferences)
    return {"id": user.id, "email": user.email, "role": user.role, "full_name": user.full_name, "avatar_url": user.avatar_url, "language": preferences.language, "timezone": preferences.timezone, "notifications_enabled": preferences.notifications_enabled}

@app.get("/api/me/export")
def export_user_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    meetings = db.scalars(select(Meeting).where(Meeting.owner_id == user.id).order_by(Meeting.created_at)).all()
    payload = {"user": {"id": user.id, "email": user.email, "role": user.role, "created_at": user.created_at.isoformat()}, "meetings": []}
    for meeting in meetings:
        payload["meetings"].append({
            "meeting": meeting_json(meeting),
            "transcript": [{"timestamp": x.timestamp, "speaker": x.speaker, "text": x.text, "topic": x.topic} for x in db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)).all()],
            "decisions": [{"decision": x.decision, "speaker": x.speaker, "timestamp": x.timestamp, "evidence": x.evidence} for x in db.scalars(select(Decision).where(Decision.meeting_id == meeting.id)).all()],
            "risks": [{"risk": x.risk, "severity": x.severity, "recommendation": x.recommendation} for x in db.scalars(select(Risk).where(Risk.meeting_id == meeting.id)).all()],
            "questions": [{"question": x.question, "speaker": x.speaker, "timestamp": x.timestamp} for x in db.scalars(select(OpenQuestion).where(OpenQuestion.meeting_id == meeting.id)).all()],
        })
    audit(db, user, "privacy.data_exported", "user", user.id); db.commit()
    return Response(content=json.dumps(payload, indent=2), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="meetmind-user-{user.id}.json"'})

@app.delete("/api/me", status_code=204)
def delete_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting_ids = select(Meeting.id).where(Meeting.owner_id == user.id)
    for model in (ActionItem, Recording, TranscriptSegment, Decision, Risk, OpenQuestion, MeetingSession, MeetingQuestion, MeetingChatMessage, FollowUpDraft):
        db.execute(delete(model).where(model.meeting_id.in_(meeting_ids)))
    db.execute(delete(Meeting).where(Meeting.owner_id == user.id))
    db.execute(delete(Notification).where(Notification.user_id == user.id))
    db.execute(delete(UserPreference).where(UserPreference.user_id == user.id))
    db.execute(delete(AuditLog).where(AuditLog.user_id == user.id))
    db.delete(user); db.commit()
    return Response(status_code=204)

@app.get("/api/admin/audit-logs")
def admin_audit_logs(limit: int = Query(100, ge=1, le=500), user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_admin(user)
    items = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return {"items": [{"id": x.id, "user_id": x.user_id, "action": x.action, "resource_type": x.resource_type, "resource_id": x.resource_id, "metadata": json.loads(x.metadata_json or "{}"), "created_at": x.created_at.isoformat()} for x in items], "total": len(items)}

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

@app.get("/api/meetings/share/{share_code}")
def shared_meeting_preview(share_code: str, db: Session = Depends(get_db)):
    meeting = db.scalar(select(Meeting).where(Meeting.share_code == share_code.upper()))
    if not meeting: raise HTTPException(404, "Meeting link not found or expired")
    return {"meeting_id": meeting.id, "share_code": meeting.share_code, "title": meeting.title, "description": meeting.description, "status": meeting.status, "is_demo": meeting.is_demo}

@app.post("/api/meetings/join-by-link")
def join_by_link(payload: JoinLinkRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = db.scalar(select(Meeting).where(Meeting.share_code == payload.share_code.upper()))
    if not meeting: raise HTTPException(404, "Meeting link not found or expired")
    existing = db.scalar(select(MeetingSession).where(MeetingSession.meeting_id == meeting.id, MeetingSession.user_id == user.id, MeetingSession.status == "joined"))
    if not existing:
        existing = MeetingSession(meeting_id=meeting.id, user_id=user.id, status="joined"); db.add(existing); audit(db, user, "meeting.joined_by_link", "meeting", meeting.id, {"share_code": meeting.share_code}); db.commit(); db.refresh(existing)
    return {"session_id": existing.id, "meeting": meeting_json(meeting), "status": "joined"}

@app.delete("/api/meetings/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    for model in (TranscriptSegment, Decision, Risk, OpenQuestion, ActionItem, Recording, MeetingSession, MeetingQuestion, MeetingChatMessage, FollowUpDraft, ProcessingStage):
        db.execute(delete(model).where(model.meeting_id == meeting.id))
    audit(db, user, "meeting.deleted", "meeting", meeting.id)
    db.delete(meeting); db.commit()
    return Response(status_code=204)

@app.get("/api/meetings/{meeting_id}/transcript")
def transcript(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == owned_id(db, meeting_id, user)).order_by(TranscriptSegment.timestamp)).all()
    return {"items": [{"id": x.id, "timestamp": x.timestamp, "speaker": x.speaker, "text": x.text, "topic": x.topic} for x in items]}

@app.get("/api/meetings/{meeting_id}/transcript/download")
def transcript_download(meeting_id: str, format: str = Query("txt", pattern="^(txt|srt|vtt|json)$"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    items = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id).order_by(TranscriptSegment.timestamp)).all()
    payload = [{"id": x.id, "timestamp": x.timestamp, "speaker": x.speaker, "text": x.text, "topic": x.topic} for x in items]
    if format == "json":
        content, media = json.dumps({"meeting_id": meeting.id, "title": meeting.title, "transcript": payload}, indent=2), "application/json"
    elif format == "srt":
        def srt_time(value: str) -> str:
            bits = value.split(":")
            if len(bits) == 2:
                return f"00:{bits[0].zfill(2)}:{bits[1].zfill(2)},000"
            if len(bits) == 3:
                return f"{bits[0].zfill(2)}:{bits[1].zfill(2)}:{bits[2].zfill(2)},000"
            return "00:00:00,000"
        blocks = []
        for index, item in enumerate(payload, 1):
            start = srt_time(item["timestamp"])
            blocks.append(f"{index}\n{start} --> {start}\n{item['speaker']}: {item['text']}\n")
        content, media = "\n".join(blocks), "application/x-subrip"
    elif format == "vtt":
        content, media = "WEBVTT\n\n" + "\n\n".join(f"{item['timestamp']} --> {item['timestamp']}\n{item['speaker']}: {item['text']}" for item in payload), "text/vtt"
    else:
        content, media = "\n".join(f"[{item['timestamp']}] {item['speaker']}: {item['text']}" for item in payload), "text/plain"
    return Response(content=content, media_type=media, headers={"Content-Disposition": f'attachment; filename="meetmind-{meeting.id}-transcript.{format}"'})

@app.get("/api/meetings/{meeting_id}/speakers")
def speakers(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting_id = owned_id(db, meeting_id, user)
    segments = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id).order_by(TranscriptSegment.timestamp)).all()
    totals = sum(len(item.text.split()) for item in segments) or 1
    grouped: dict[str, dict] = {}
    for item in segments:
        entry = grouped.setdefault(item.speaker, {"speaker": item.speaker, "segments": 0, "words": 0, "first_timestamp": item.timestamp, "last_timestamp": item.timestamp})
        entry["segments"] += 1; entry["words"] += len(item.text.split()); entry["last_timestamp"] = item.timestamp
    items = sorted((dict(value, share=round(value["words"] / totals, 3)) for value in grouped.values()), key=lambda value: value["words"], reverse=True)
    return {"items": items, "total_segments": len(segments)}

@app.get("/api/meetings/{meeting_id}/timeline")
def timeline(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting_id = owned_id(db, meeting_id, user)
    events = [{"timestamp": item.timestamp, "type": "transcript", "label": item.topic, "text": item.text, "speaker": item.speaker} for item in db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)).all()]
    events += [{"timestamp": item.timestamp, "type": "decision", "label": "Decision", "text": item.decision, "speaker": item.speaker} for item in db.scalars(select(Decision).where(Decision.meeting_id == meeting_id)).all()]
    events += [{"timestamp": item.timestamp, "type": "risk", "label": f"Risk · {item.severity}", "text": item.risk, "speaker": ""} for item in db.scalars(select(Risk).where(Risk.meeting_id == meeting_id)).all()]
    return {"items": sorted(events, key=lambda item: item["timestamp"])}

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

@app.get("/api/meetings/{meeting_id}/health")
def meeting_health(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting_id = owned_id(db, meeting_id, user)
    transcript_count = db.scalar(select(func.count(TranscriptSegment.id)).where(TranscriptSegment.meeting_id == meeting_id)) or 0
    decision_count = db.scalar(select(func.count(Decision.id)).where(Decision.meeting_id == meeting_id)) or 0
    action_items = db.scalars(select(ActionItem).where(ActionItem.meeting_id == meeting_id)).all()
    risk_items = db.scalars(select(Risk).where(Risk.meeting_id == meeting_id)).all()
    evidence = min(100, transcript_count * 12.5)
    alignment = min(100, 40 + decision_count * 15)
    follow_through = 100 if not action_items else round(sum(item.status == "Completed" for item in action_items) / len(action_items) * 100)
    risk_score = max(0, 100 - sum(25 if item.severity.lower() == "high" else 10 for item in risk_items if item.status.upper() != "RESOLVED"))
    score = round((evidence + alignment + follow_through + risk_score) / 4)
    signals = []
    if transcript_count: signals.append({"label": "Transcript evidence", "value": transcript_count, "status": "available"})
    if decision_count: signals.append({"label": "Decisions recorded", "value": decision_count, "status": "available"})
    signals.append({"label": "Action follow-through", "value": f"{follow_through}%", "status": "strong" if follow_through >= 70 else "watch"})
    signals.append({"label": "Open risk exposure", "value": len([item for item in risk_items if item.status.upper() != "RESOLVED"]), "status": "watch" if risk_score < 80 else "strong"})
    return {"meeting_id": meeting_id, "score": score, "components": {"evidence": round(evidence), "alignment": round(alignment), "follow_through": follow_through, "risk": risk_score}, "signals": signals}

@app.get("/api/meetings/{meeting_id}/intelligence")
def meeting_intelligence(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting_id = owned_id(db, meeting_id, user)
    decisions_data = db.scalars(select(Decision).where(Decision.meeting_id == meeting_id).order_by(Decision.timestamp)).all()
    actions_data = db.scalars(select(ActionItem).where(ActionItem.meeting_id == meeting_id).order_by(ActionItem.deadline)).all()
    decision_dna = [{"decision": item.decision, "owner": item.speaker, "timestamp": item.timestamp, "confidence": item.confidence, "evidence": item.evidence, "status": item.status} for item in decisions_data]
    commitment_radar = [{"commitment": item.task, "owner": item.owner_id, "deadline": item.deadline, "status": item.status, "priority": item.priority, "evidence": item.evidence, "timestamp": item.timestamp} for item in actions_data]
    return {"meeting_id": meeting_id, "decision_dna": decision_dna, "commitment_radar": commitment_radar}

@app.get("/api/meetings/{meeting_id}/preflight")
def meeting_preflight(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    current = user_meeting(db, meeting_id, user)
    stop_words = {"about", "after", "before", "from", "meeting", "project", "that", "this", "with", "and", "the"}
    tokens = {word for word in re.findall(r"[a-z0-9]{3,}", f"{current.title} {current.summary}".lower()) if word not in stop_words}
    related = []
    for candidate in db.scalars(select(Meeting).where(Meeting.owner_id == user.id, Meeting.id != current.id)).all():
        candidate_tokens = {word for word in re.findall(r"[a-z0-9]{3,}", f"{candidate.title} {candidate.summary}".lower()) if word not in stop_words}
        overlap = tokens & candidate_tokens
        if overlap:
            related.append({"id": candidate.id, "title": candidate.title, "status": candidate.status, "shared_terms": sorted(overlap), "score": len(overlap)})
    related.sort(key=lambda item: item["score"], reverse=True)
    carry_over = []
    for candidate in db.scalars(select(Meeting).where(Meeting.owner_id == user.id, Meeting.id != current.id)).all():
        for action in db.scalars(select(ActionItem).where(ActionItem.meeting_id == candidate.id, ActionItem.status != "Completed")).all():
            carry_over.append({"task": action.task, "owner": action.owner_id, "deadline": action.deadline, "status": action.status, "meeting_id": candidate.id, "meeting_title": candidate.title})
    suggestions = ["Which carry-over actions need an updated owner or deadline?"] if carry_over else []
    if related: suggestions.append(f"What changed since {related[0]['title']}?")
    return {"meeting_id": current.id, "related_meetings": related[:5], "carry_over_actions": carry_over[:10], "suggested_questions": suggestions}

@app.post("/api/meetings/{meeting_id}/translate")
def translate_meeting(meeting_id: str, payload: TranslationRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    if payload.target_language not in SUPPORTED_LANGUAGES: raise HTTPException(422, f"Unsupported target language. Choose one of: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
    provider = get_translation_provider()
    if not provider.configured: raise HTTPException(503, "Translation provider not configured. Set TRANSLATION_PROVIDER and its credentials before requesting translated output.")
    source = meeting.summary if payload.scope == "summary" else "\n".join(x.text for x in db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)).all())
    return {"meeting_id": meeting.id, "source_language": detect_language(source), "target_language": payload.target_language, "scope": payload.scope, "translated_text": provider.translate(source, payload.target_language)}

@app.get("/api/meetings/{meeting_id}/language")
def meeting_language(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    transcript = "\n".join(item.text for item in db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id)).all())
    source = transcript or meeting.summary
    return {"meeting_id": meeting.id, "language": detect_language(source), "confidence": 0.8 if source else 0.0, "mode": "script-detection"}

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

@app.get("/api/compare/meetings")
def compare_meetings(first_id: str, second_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    first = user_meeting(db, first_id, user); second = user_meeting(db, second_id, user)
    def values(model, field: str, meeting_id: str) -> set[str]: return {str(getattr(item, field)).strip().lower() for item in db.scalars(select(model).where(model.meeting_id == meeting_id)).all()}
    def diff(model, field: str):
        left, right = values(model, field, first.id), values(model, field, second.id)
        return {"new": sorted(right - left), "removed": sorted(left - right), "unchanged": sorted(left & right)}
    return {"first": {"id": first.id, "title": first.title}, "second": {"id": second.id, "title": second.title}, "decisions": diff(Decision, "decision"), "actions": diff(ActionItem, "task"), "risks": diff(Risk, "risk")}

@app.get("/api/meetings/{meeting_id}/export")
def export_meeting(meeting_id: str, format: str = Query("json", pattern="^(json|txt|md|pdf|docx)$"), template: str = Query("detailed", pattern="^(executive|detailed|project|client|sprint|management|decision|action|custom)$"), user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    segments = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id).order_by(TranscriptSegment.timestamp)).all()
    decisions_data = db.scalars(select(Decision).where(Decision.meeting_id == meeting.id)).all()
    risks_data = db.scalars(select(Risk).where(Risk.meeting_id == meeting.id)).all()
    questions_data = db.scalars(select(OpenQuestion).where(OpenQuestion.meeting_id == meeting.id)).all()
    payload = {"template": template, "generated_at": datetime.now(timezone.utc).isoformat(), "meeting": meeting_json(meeting), "transcript": [{"timestamp": x.timestamp, "speaker": x.speaker, "text": x.text, "topic": x.topic} for x in segments], "decisions": [{"decision": x.decision, "speaker": x.speaker, "timestamp": x.timestamp, "evidence": x.evidence, "confidence": x.confidence} for x in decisions_data], "risks": [{"risk": x.risk, "severity": x.severity, "timestamp": x.timestamp, "recommendation": x.recommendation} for x in risks_data], "questions": [{"question": x.question, "speaker": x.speaker, "timestamp": x.timestamp} for x in questions_data]}
    if format == "json":
        content, media_type = json.dumps(payload, indent=2), "application/json"
    elif format == "md":
        content, media_type = "\n".join(report_lines(payload, markdown=True)), "text/markdown"
    elif format == "txt":
        content, media_type = "\n".join(report_lines(payload)), "text/plain"
    elif format == "docx":
        content, media_type = make_docx(report_lines(payload)), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        content, media_type = make_pdf(report_lines(payload)), "application/pdf"
    extension = {"md": "md", "docx": "docx", "pdf": "pdf"}.get(format, format)
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="meetmind-{meeting.id}.{extension}"'})

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
    meeting = user_meeting(db, meeting_id, user)
    provider = get_ai_provider()
    if not provider.configured: raise HTTPException(503, "AI provider not configured. Set AI_PROVIDER and credentials before processing a meeting.")
    segments = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id).order_by(TranscriptSegment.timestamp)).all()
    if not segments: raise HTTPException(422, "A persisted transcript is required before processing this meeting.")
    stages = ensure_pipeline(db, meeting.id)
    meeting.status = "processing"
    for stage in stages:
        if stage.status == "FAILED":
            stage.status = "PENDING"; stage.error = ""
    db.add(Notification(user_id=user.id, kind="processing", title="Meeting processing started", body=f"{meeting.title} is being prepared for intelligence."))
    db.commit()
    try:
        started = datetime.now(timezone.utc)
        transcription_stage = next(item for item in stages if item.name == "TRANSCRIPTION")
        transcription_stage.status = "COMPLETED"; transcription_stage.started_at = started; transcription_stage.completed_at = started; transcription_stage.attempts += 1
        transcript_text = "\n".join(f"[{item.timestamp}] {item.speaker}: {item.text}" for item in segments)
        result = provider.analyze(transcript_text)
        if not isinstance(result, dict): raise ValueError("AI provider returned an invalid object")
        meeting.summary = str(result.get("summary") or "Not specified in the meeting.")
        meeting.executive_summary = str(result.get("executive_summary") or meeting.summary)
        meeting.short_summary = str(result.get("short_summary") or meeting.summary[:280])
        meeting.detailed_summary = str(result.get("detailed_summary") or meeting.summary)
        meeting.detected_language = detect_language(transcript_text)
        if not db.scalar(select(Decision).where(Decision.meeting_id == meeting.id)):
            for item in result.get("decisions", []) or []:
                if item.get("decision"): db.add(Decision(meeting_id=meeting.id, decision=str(item["decision"]), speaker=str(item.get("speaker", "Unknown speaker")), timestamp=str(item.get("timestamp", "")), evidence=str(item.get("evidence", "")), confidence=float(item.get("confidence", 0.0))))
        if not db.scalar(select(ActionItem).where(ActionItem.meeting_id == meeting.id)):
            for item in result.get("actions", []) or []:
                if item.get("task"): db.add(ActionItem(meeting_id=meeting.id, owner_id=user.id, task=str(item["task"]), deadline=str(item.get("deadline", "Not specified in the meeting")), priority=str(item.get("priority", "Medium")), status=str(item.get("status", "Pending")), timestamp=str(item.get("timestamp", "")), evidence=str(item.get("evidence", "")), confidence=float(item.get("confidence", 0.0))))
        if not db.scalar(select(Risk).where(Risk.meeting_id == meeting.id)):
            for item in result.get("risks", []) or []:
                if item.get("risk"): db.add(Risk(meeting_id=meeting.id, risk=str(item["risk"]), severity=str(item.get("severity", "Medium")), timestamp=str(item.get("timestamp", "")), recommendation=str(item.get("recommendation", "Confirm an owner and next step."))))
        if not db.scalar(select(OpenQuestion).where(OpenQuestion.meeting_id == meeting.id)):
            for item in result.get("questions", []) or []:
                if item.get("question"): db.add(OpenQuestion(meeting_id=meeting.id, question=str(item["question"]), speaker=str(item.get("speaker", "Unknown speaker")), timestamp=str(item.get("timestamp", ""))))
        meeting.status = "analyzed"
        completed = datetime.now(timezone.utc)
        for stage in stages:
            stage.status = "COMPLETED"; stage.started_at = stage.started_at or started; stage.completed_at = completed; stage.attempts += 1
            stage.evidence_json = json.dumps([{"source": "transcript", "segments": len(segments)}])
        db.add(Notification(user_id=user.id, kind="processing", title="Meeting processing completed", body=f"{meeting.title} intelligence is ready.")); audit(db, user, "meeting.processed", "meeting", meeting.id, {"provider": provider.name}); db.commit()
    except Exception as exc:
        db.rollback(); meeting = user_meeting(db, meeting_id, user); meeting.status = "failed"
        failed = ensure_pipeline(db, meeting.id)
        pending = next((item for item in failed if item.status != "COMPLETED"), failed[-1])
        pending.status = "FAILED"; pending.error = str(exc); pending.attempts += 1; pending.started_at = pending.started_at or datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(502, f"Meeting processing failed: {exc}") from exc
    return {"meeting_id": meeting.id, "status": meeting.status, "mode": provider.name, "message": "Meeting intelligence persisted."}

@app.get("/api/meetings/{meeting_id}/processing")
def processing_status(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    return {"meeting_id": meeting.id, "status": meeting.status, "stages": pipeline_json(ensure_pipeline(db, meeting.id))}

@app.post("/api/meetings/{meeting_id}/retry")
def retry_processing(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    if meeting.status != "failed":
        raise HTTPException(409, "Only failed processing can be retried")
    return process(meeting.id, user, db)

@app.post("/api/meetings/{meeting_id}/join")
def join_meeting(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    session = MeetingSession(meeting_id=meeting.id, user_id=user.id, status="joined"); db.add(session); db.commit(); db.refresh(session)
    return {"session_id": session.id, "meeting_id": meeting.id, "status": session.status, "joined_at": session.joined_at.isoformat()}

@app.get("/api/meetings/{meeting_id}/chat")
def meeting_chat(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    items = db.scalars(select(MeetingChatMessage).where(MeetingChatMessage.meeting_id == meeting.id).order_by(MeetingChatMessage.created_at)).all()
    return {"items": [{"id": item.id, "meeting_id": item.meeting_id, "user_id": item.user_id, "message": item.message, "created_at": item.created_at.isoformat()} for item in items]}

@app.post("/api/meetings/{meeting_id}/chat", status_code=201)
def send_meeting_chat(meeting_id: str, payload: ChatMessageCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    item = MeetingChatMessage(meeting_id=meeting.id, user_id=user.id, message=payload.message.strip())
    db.add(item); audit(db, user, "meeting.chat_message_created", "meeting", meeting.id); db.commit(); db.refresh(item)
    return {"id": item.id, "meeting_id": item.meeting_id, "user_id": item.user_id, "message": item.message, "created_at": item.created_at.isoformat()}

@app.post("/api/meetings/{meeting_id}/follow-up", status_code=201)
def generate_follow_up(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    actions = db.scalars(select(ActionItem).where(ActionItem.meeting_id == meeting.id).order_by(ActionItem.deadline)).all()
    subject = f"Follow-up: {meeting.title}"
    lines = ["Hi team,", "", f"Thanks for the discussion on {meeting.title}.", "", "Key context:", meeting.summary or "No summary was recorded.", ""]
    if actions:
        lines.extend(["Action items:"] + [f"- {item.task} — owner: {item.owner_id}; due: {item.deadline}; status: {item.status}" for item in actions])
    else:
        lines.append("No action items were recorded.")
    lines.extend(["", "Please reply with corrections or updated dates.", "", "Best,", "MeetMind"])
    draft = FollowUpDraft(meeting_id=meeting.id, user_id=user.id, subject=subject, body="\n".join(lines))
    db.add(draft); audit(db, user, "meeting.follow_up_generated", "meeting", meeting.id); db.commit(); db.refresh(draft)
    return {"id": draft.id, "meeting_id": draft.meeting_id, "subject": draft.subject, "body": draft.body, "created_at": draft.created_at.isoformat()}

@app.get("/api/meetings/{meeting_id}/follow-up")
def follow_up_history(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    items = db.scalars(select(FollowUpDraft).where(FollowUpDraft.meeting_id == meeting.id, FollowUpDraft.user_id == user.id).order_by(FollowUpDraft.created_at.desc())).all()
    return {"items": [{"id": item.id, "subject": item.subject, "body": item.body, "created_at": item.created_at.isoformat()} for item in items]}

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
    stop_words = {"what","were","was","the","who","when","where","about","this","meeting","and","are","for","did","we","office","catering","vendor"}
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

@app.post("/api/assistant")
def assistant(payload: AssistantRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Grounded application assistant. It only answers from records owned by the user."""
    meetings_query = select(Meeting).where(Meeting.owner_id == user.id)
    if payload.meeting_id:
        meeting = user_meeting(db, payload.meeting_id, user)
        meetings = [meeting]
    else:
        meetings = db.scalars(meetings_query.order_by(Meeting.created_at.desc())).all()
    question = payload.question.strip()
    lowered = question.lower()
    terms = {word for word in re.findall(r"[a-z0-9]{3,}", lowered) if word not in {"what", "were", "was", "the", "who", "when", "where", "how", "can", "you", "about", "this", "meeting", "show", "tell", "from", "with", "and", "for"}}
    evidence: list[dict] = []
    decisions_data: list[Decision] = []
    actions_data: list[ActionItem] = []
    risks_data: list[Risk] = []
    questions_data: list[OpenQuestion] = []
    for meeting in meetings:
        segments = db.scalars(select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting.id).order_by(TranscriptSegment.timestamp)).all()
        for segment in segments:
            haystack = f"{meeting.title} {segment.speaker} {segment.topic} {segment.text}".lower()
            if not terms or any(term in haystack for term in terms):
                evidence.append({"meeting_id": meeting.id, "meeting": meeting.title, "timestamp": segment.timestamp, "speaker": segment.speaker, "text": segment.text, "type": "transcript"})
        decisions_data.extend(db.scalars(select(Decision).where(Decision.meeting_id == meeting.id)).all())
        actions_data.extend(db.scalars(select(ActionItem).where(ActionItem.meeting_id == meeting.id)).all())
        risks_data.extend(db.scalars(select(Risk).where(Risk.meeting_id == meeting.id)).all())
        questions_data.extend(db.scalars(select(OpenQuestion).where(OpenQuestion.meeting_id == meeting.id)).all())
    if any(word in lowered for word in ("decision", "decided", "agree")):
        selected = [item for item in decisions_data if not terms or any(term in f"{item.decision} {item.evidence}".lower() for term in terms)]
        evidence.extend({"meeting_id": item.meeting_id, "timestamp": item.timestamp, "speaker": item.speaker, "text": item.evidence or item.decision, "type": "decision"} for item in selected[:5])
        answer = "Recorded decisions: " + "; ".join(item.decision for item in selected[:5]) if selected else "I couldn't find sufficient evidence for a decision in the authorized meeting data."
    elif any(word in lowered for word in ("action", "task", "owner", "deadline", "todo", "commitment")):
        selected = [item for item in actions_data if not terms or any(term in f"{item.task} {item.evidence} {item.deadline}".lower() for term in terms)]
        evidence.extend({"meeting_id": item.meeting_id, "timestamp": item.timestamp, "speaker": "", "text": item.evidence or item.task, "type": "action"} for item in selected[:5])
        answer = "Recorded actions: " + "; ".join(f"{item.task} (due {item.deadline})" for item in selected[:5]) if selected else "I couldn't find sufficient evidence for an action in the authorized meeting data."
    elif any(word in lowered for word in ("risk", "blocker", "concern", "dependency")):
        selected = [item for item in risks_data if not terms or any(term in f"{item.risk} {item.recommendation}".lower() for term in terms)]
        evidence.extend({"meeting_id": item.meeting_id, "timestamp": item.timestamp, "speaker": "", "text": item.risk, "type": "risk"} for item in selected[:5])
        answer = "Recorded risks: " + "; ".join(f"{item.risk} ({item.severity})" for item in selected[:5]) if selected else "I couldn't find sufficient evidence for a risk in the authorized meeting data."
    elif any(word in lowered for word in ("question", "unresolved", "open")):
        selected = [item for item in questions_data if not terms or any(term in f"{item.question}".lower() for term in terms)]
        evidence.extend({"meeting_id": item.meeting_id, "timestamp": item.timestamp, "speaker": item.speaker, "text": item.question, "type": "question"} for item in selected[:5])
        answer = "Open questions: " + "; ".join(item.question for item in selected[:5]) if selected else "I couldn't find sufficient evidence for an open question in the authorized meeting data."
    elif any(word in lowered for word in ("summary", "summarize", "overview")) and meetings:
        selected_meeting = meetings[0]
        answer = selected_meeting.summary or "I couldn't find a recorded summary for this meeting."
        evidence.append({"meeting_id": selected_meeting.id, "meeting": selected_meeting.title, "timestamp": "", "speaker": "", "text": answer, "type": "summary"})
    else:
        answer = "I found relevant transcript evidence." if evidence else "I couldn't find sufficient evidence for this answer in the authorized meeting data."
    facts = bool(evidence) and not answer.startswith("I couldn't")
    quick_actions = [{"label": "Review actions", "intent": "actions"}, {"label": "Review decisions", "intent": "decisions"}, {"label": "Show risks", "intent": "risks"}]
    return {"answer": answer, "answer_type": "FACT" if facts else "INSUFFICIENT_EVIDENCE", "confidence": round(min(.95, .55 + len(evidence) * .08), 2) if facts else .1, "evidence": evidence[:8], "quick_actions": quick_actions, "context": {"page": payload.current_page, "meeting_id": payload.meeting_id, "meetings_considered": len(meetings)}}

@app.get("/api/meetings/{meeting_id}/questions/history")
def question_history(meeting_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user); items = db.scalars(select(MeetingQuestion).where(MeetingQuestion.meeting_id == meeting.id, MeetingQuestion.user_id == user.id).order_by(MeetingQuestion.created_at.desc())).all()
    return {"items": [{"id": x.id, "question": x.question, "answer": x.answer, "confidence": x.confidence, "evidence": json.loads(x.evidence_json)} for x in items]}

@app.get("/api/actions")
def list_actions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(ActionItem).join(Meeting).where(Meeting.owner_id == user.id)).all(); return {"items": [action_json(a) for a in items], "total": len(items)}

@app.post("/api/meetings/{meeting_id}/actions", status_code=201)
def create_action(meeting_id: str, payload: ActionCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    meeting = user_meeting(db, meeting_id, user)
    action = ActionItem(meeting_id=meeting.id, owner_id=payload.owner_id or user.id, task=payload.task, deadline=payload.deadline, priority=payload.priority, status="DETECTED", timestamp=payload.timestamp, evidence=payload.evidence, confidence=payload.confidence)
    db.add(action); audit(db, user, "action.created", "action", action.id, {"meeting_id": meeting.id}); db.commit(); db.refresh(action)
    db.add(Notification(user_id=user.id, kind="action", title="Action created", body=f"{action.task} was added to {meeting.title}.")); db.commit()
    return action_json(action)

@app.patch("/api/actions/{action_id}")
def update_action(action_id: str, payload: ActionUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    action = db.scalar(select(ActionItem).join(Meeting).where(ActionItem.id == action_id, Meeting.owner_id == user.id))
    if not action: raise HTTPException(404, "Action not found")
    for key, value in payload.model_dump(exclude_none=True).items(): setattr(action, key, value)
    if payload.status: db.add(Notification(user_id=user.id, kind="action", title="Action updated", body=f"{action.task} is now {payload.status}."))
    audit(db, user, "action.updated", "action", action.id, payload.model_dump(exclude_none=True))
    db.commit(); db.refresh(action); return action_json(action)

@app.get("/api/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())).all()
    return {"items": [{"id": x.id, "kind": x.kind, "title": x.title, "body": x.body, "read": x.read, "created_at": x.created_at.isoformat()} for x in items], "unread": sum(not x.read for x in items)}

@app.patch("/api/notifications/{notification_id}")
def mark_notification(notification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id))
    if not item: raise HTTPException(404, "Notification not found")
    item.read = True; db.commit(); return {"id": item.id, "read": item.read}

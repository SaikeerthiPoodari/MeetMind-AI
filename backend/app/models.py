from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def now() -> datetime: return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="ORGANIZER")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    owner: Mapped[User] = relationship(back_populates="meetings")
    actions: Mapped[list["ActionItem"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")

class ActionItem(Base):
    __tablename__ = "action_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    task: Mapped[str] = mapped_column(String(300))
    deadline: Mapped[str] = mapped_column(String(80), default="Not specified in the meeting")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(30), default="Pending")
    evidence: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[str] = mapped_column(String(20), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    meeting: Mapped[Meeting] = relationship(back_populates="actions")

class Recording(Base):
    __tablename__ = "recordings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    storage_path: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    timestamp: Mapped[str] = mapped_column(String(20), index=True)
    speaker: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(120), default="")

class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    decision: Mapped[str] = mapped_column(Text)
    speaker: Mapped[str] = mapped_column(String(120))
    timestamp: Mapped[str] = mapped_column(String(20))
    evidence: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="CONFIRMED")

class Risk(Base):
    __tablename__ = "risks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    risk: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[str] = mapped_column(String(20))
    recommendation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")

class OpenQuestion(Base):
    __tablename__ = "open_questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    speaker: Mapped[str] = mapped_column(String(120))
    timestamp: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")

class MeetingSession(Base):
    __tablename__ = "meeting_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="joined")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

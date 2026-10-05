"""Add persisted meeting chat messages."""
from alembic import op
from app import models

revision = "0004_meeting_chat"
down_revision = "0003_audit_logs"
branch_labels = None
depends_on = None

def upgrade() -> None:
    models.MeetingChatMessage.__table__.create(bind=op.get_bind(), checkfirst=True)

def downgrade() -> None:
    models.MeetingChatMessage.__table__.drop(bind=op.get_bind(), checkfirst=True)

"""Add persisted follow-up drafts."""
from alembic import op
from app import models

revision = "0005_follow_up_drafts"
down_revision = "0004_meeting_chat"
branch_labels = None
depends_on = None

def upgrade() -> None:
    models.FollowUpDraft.__table__.create(bind=op.get_bind(), checkfirst=True)

def downgrade() -> None:
    models.FollowUpDraft.__table__.drop(bind=op.get_bind(), checkfirst=True)

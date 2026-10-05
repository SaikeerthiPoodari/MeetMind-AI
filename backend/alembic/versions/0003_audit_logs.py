"""Add persisted audit logs."""
from alembic import op
from app import models

revision = "0003_audit_logs"
down_revision = "0002_user_preferences"
branch_labels = None
depends_on = None

def upgrade() -> None:
    models.AuditLog.__table__.create(bind=op.get_bind(), checkfirst=True)

def downgrade() -> None:
    models.AuditLog.__table__.drop(bind=op.get_bind(), checkfirst=True)

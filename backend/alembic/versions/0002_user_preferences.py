"""Add persisted user preferences."""
from alembic import op
from app.db import Base
from app import models  # noqa: F401

revision = "0002_user_preferences"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

def upgrade() -> None:
    UserPreference = models.UserPreference
    UserPreference.__table__.create(bind=op.get_bind(), checkfirst=True)

def downgrade() -> None:
    models.UserPreference.__table__.drop(bind=op.get_bind(), checkfirst=True)

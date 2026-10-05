"""Add editable user profile fields."""
from alembic import op
import sqlalchemy as sa

revision = "0008_user_profile"
down_revision = "0007_meeting_sharing"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=160), server_default="", nullable=False))
    op.add_column("users", sa.Column("avatar_url", sa.Text(), server_default="", nullable=False))

def downgrade() -> None:
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "full_name")

"""Add shareable meeting codes."""
from alembic import op
import sqlalchemy as sa
import secrets

revision = "0007_meeting_sharing"
down_revision = "0006_processing_pipeline"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("meetings", sa.Column("share_code", sa.String(length=20), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id FROM meetings WHERE share_code IS NULL")).fetchall()
    for row in rows:
        connection.execute(sa.text("UPDATE meetings SET share_code = :code WHERE id = :id"), {"code": secrets.token_hex(5).upper(), "id": row[0]})
    op.create_index("ix_meetings_share_code", "meetings", ["share_code"], unique=True)

def downgrade() -> None:
    op.drop_index("ix_meetings_share_code", table_name="meetings")
    op.drop_column("meetings", "share_code")

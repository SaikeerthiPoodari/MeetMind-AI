"""Add resumable processing state and summary variants."""
from alembic import op
import sqlalchemy as sa

revision = "0006_processing_pipeline"
down_revision = "0005_follow_up_drafts"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("meetings", sa.Column("executive_summary", sa.Text(), server_default="", nullable=False))
    op.add_column("meetings", sa.Column("short_summary", sa.Text(), server_default="", nullable=False))
    op.add_column("meetings", sa.Column("detailed_summary", sa.Text(), server_default="", nullable=False))
    op.add_column("meetings", sa.Column("detected_language", sa.String(length=12), server_default="und", nullable=False))
    op.create_table(
        "processing_stages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("meeting_id", sa.String(length=36), sa.ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_processing_stages_meeting_id", "processing_stages", ["meeting_id"])
    op.create_index("ix_processing_stages_name", "processing_stages", ["name"])

def downgrade() -> None:
    op.drop_table("processing_stages")
    for column in ("detected_language", "detailed_summary", "short_summary", "executive_summary"):
        op.drop_column("meetings", column)

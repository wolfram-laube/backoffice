"""001_initial — Create applications, crawl_results, application_history.

Revision ID: 001_initial
Revises: None
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- applications ---
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("date_recorded", sa.Date(), nullable=True),
        sa.Column("project_title", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Text(), nullable=True),
        sa.Column("duration", sa.Text(), nullable=True),
        sa.Column("workload", sa.Text(), nullable=True),
        sa.Column("rate_eur_h", sa.Float(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_date", "applications", ["date_recorded"])
    op.create_index("ix_applications_status", "applications", ["status"])
    op.create_index("ix_applications_provider", "applications", ["provider"])
    op.create_index("ix_applications_match_score", "applications", ["match_score"])

    # --- crawl_results ---
    op.create_table(
        "crawl_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("match_reasons", sa.JSON(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="new"),
        sa.Column("crawled_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_crawl_source_extid",
        "crawl_results",
        ["source", "external_id"],
        unique=True,
    )
    op.create_index("ix_crawl_status", "crawl_results", ["status"])

    # --- application_history ---
    op.create_table(
        "application_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("field_changed", sa.Text(), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_history_app_id", "application_history", ["application_id"])
    op.create_index("ix_history_changed_at", "application_history", ["changed_at"])


def downgrade() -> None:
    op.drop_table("application_history")
    op.drop_table("crawl_results")
    op.drop_table("applications")

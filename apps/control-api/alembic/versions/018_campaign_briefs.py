"""create campaign_briefs table (BP-004)

Revision ID: 018
Revises: 017
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "campaign_briefs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advertiser_organization_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("product_category", sa.String(255), nullable=True),
        sa.Column("target_period_from", sa.Date(), nullable=True),
        sa.Column("target_period_to", sa.Date(), nullable=True),
        sa.Column("budget_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("budget_currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("preferred_channels", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_campaign_briefs_org_id", "campaign_briefs", ["advertiser_organization_id"])
    op.create_index("ix_campaign_briefs_status", "campaign_briefs", ["status"])
    op.create_foreign_key("fk_brief_org", "campaign_briefs",
                          "advertiser_organizations", ["advertiser_organization_id"], ["id"])
    op.create_foreign_key("fk_brief_created_by", "campaign_briefs",
                          "users", ["created_by"], ["id"])


def downgrade():
    op.drop_table("campaign_briefs")

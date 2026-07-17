"""create advertiser_invites table (BP-002)

Revision ID: 017
Revises: 016
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "advertiser_invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advertiser_application_id", sa.String(36), nullable=True),
        sa.Column("advertiser_organization_id", sa.String(36), nullable=False),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by_user_id", sa.String(36), nullable=True),
    )
    op.create_index("ix_advertiser_invites_application_id", "advertiser_invites", ["advertiser_application_id"])
    op.create_index("ix_advertiser_invites_org_id", "advertiser_invites", ["advertiser_organization_id"])
    op.create_index("ix_advertiser_invites_status", "advertiser_invites", ["status"])
    op.create_foreign_key("fk_invite_application", "advertiser_invites",
                          "advertiser_applications", ["advertiser_application_id"], ["id"])
    op.create_foreign_key("fk_invite_org", "advertiser_invites",
                          "advertiser_organizations", ["advertiser_organization_id"], ["id"])
    op.create_foreign_key("fk_invite_created_by", "advertiser_invites",
                          "users", ["created_by"], ["id"])
    op.create_foreign_key("fk_invite_accepted_by", "advertiser_invites",
                          "users", ["accepted_by_user_id"], ["id"])


def downgrade():
    op.drop_table("advertiser_invites")

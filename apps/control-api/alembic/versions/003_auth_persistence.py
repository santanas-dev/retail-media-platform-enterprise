"""${message}

Revision ID: 003
Revises: 002
Create Date: 2026-07-02

Phase 3.2a: Auth persistence schema.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Advertiser Organizations
    # -----------------------------------------------------------------------
    op.create_table(
        "advertiser_organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # Advertiser User Memberships
    # -----------------------------------------------------------------------
    op.create_table(
        "advertiser_user_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"),
                  nullable=False, index=True),
        sa.Column("advertiser_organization_id", sa.String(36),
                  sa.ForeignKey("advertiser_organizations.id"),
                  nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "advertiser_organization_id",
                            name="uq_adv_membership"),
    )

    # -----------------------------------------------------------------------
    # Local Credentials
    # -----------------------------------------------------------------------
    op.create_table(
        "local_credentials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"),
                  nullable=False, unique=True, index=True),
        sa.Column("credential_type", sa.String(32), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False, server_default=""),
        sa.Column("password_hash_algorithm", sa.String(32), nullable=False,
                  server_default="bcrypt"),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "credential_type IN ('local_advertiser', 'local_break_glass')",
            name="ck_lc_credential_type",
        ),
    )

    # -----------------------------------------------------------------------
    # Refresh Sessions
    # -----------------------------------------------------------------------
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"),
                  nullable=False, index=True),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("token_family_id", sa.String(36), nullable=False, index=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # Login Attempts
    # -----------------------------------------------------------------------
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username_or_email_hash", sa.String(128), nullable=False, index=True),
        sa.Column("auth_provider", sa.String(32), nullable=False, index=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()"), index=True),
    )

    # -----------------------------------------------------------------------
    # Password Reset Tokens
    # -----------------------------------------------------------------------
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"),
                  nullable=False, index=True),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("login_attempts")
    op.drop_table("refresh_sessions")
    op.drop_table("local_credentials")
    op.drop_table("advertiser_user_memberships")
    op.drop_table("advertiser_organizations")

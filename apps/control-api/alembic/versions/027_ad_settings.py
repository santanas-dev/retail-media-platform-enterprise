"""G4-FIX: ad_settings table for durable AD/LDAPS configuration

Revision ID: 027
Revises: 026
Create Date: 2026-07-20

Singleton table — single row (id=1). No bind_password column — that
remains env-only (AD_BIND_PASSWORD) and is never stored in the DB.
"""

from alembic import op
import sqlalchemy as sa

revision = "027"
down_revision = "026"


def upgrade():
    op.create_table(
        "ad_settings",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("server_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_dn", sa.Text(), nullable=False, server_default=""),
        sa.Column("user_search_base", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "user_search_filter",
            sa.Text(),
            nullable=False,
            server_default="(sAMAccountName={username})",
        ),
        sa.Column("bind_dn", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "use_tls", sa.Boolean(), nullable=False, server_default="true",
        ),
        sa.Column(
            "certificate_validation",
            sa.String(16),
            nullable=False,
            server_default="required",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Insert default row
    op.execute(
        "INSERT INTO ad_settings (id) VALUES (1) "
        "ON CONFLICT (id) DO NOTHING"
    )


def downgrade():
    op.drop_table("ad_settings")

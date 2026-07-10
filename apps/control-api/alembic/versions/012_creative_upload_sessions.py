"""Creative upload sessions — presigned URL tracking (S-017)

Revision ID: 012
Revises: 011
Create Date: 2026-07-10

Tracks upload-intent → presigned PUT → complete-upload lifecycle.
The session proves the exact upload parameters (filename, content_type,
content_length) were authorised at intent time.  complete-upload uses the
upload_id to verify the session is still valid, not expired, and matches
the creative asset.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "creative_upload_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "creative_asset_id", sa.String(36),
            sa.ForeignKey("creative_assets.id"), nullable=False, index=True,
        ),
        sa.Column(
            "advertiser_organization_id", sa.String(36),
            sa.ForeignKey("advertiser_organizations.id"), nullable=False, index=True,
        ),
        sa.Column("storage_bucket", sa.String(128), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("content_length", sa.Integer, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36),
                   sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                   server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("content_length > 0",
                           name="ck_cus_content_length_positive"),
        sa.CheckConstraint("content_type != ''",
                           name="ck_cus_content_type_not_empty"),
    )


def downgrade() -> None:
    op.drop_table("creative_upload_sessions")

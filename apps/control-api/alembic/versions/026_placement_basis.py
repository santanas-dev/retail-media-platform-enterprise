"""G1-FIX: add placement_basis to campaigns

Revision ID: 026
Revises: 025
Create Date: 2026-07-18

Values: commercial (коммерческое), internal (внутреннее),
compensation (компенсация/make-good), test (тестовое).
"""

from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"


def upgrade():
    op.add_column(
        "campaigns",
        sa.Column(
            "placement_basis",
            sa.String(32),
            nullable=False,
            server_default="commercial",
        ),
    )


def downgrade():
    op.drop_column("campaigns", "placement_basis")

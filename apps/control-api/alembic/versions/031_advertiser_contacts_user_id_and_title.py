"""031: Add user_id foreign key + title to advertiser_contacts.

Supports advertiser contact CRUD + optional user account link (ADVERTISER-UX-001B3).
user_id is nullable — existing contacts without user link remain valid.
FK references users(id), ON DELETE SET NULL.
"""

from alembic import op
import sqlalchemy as sa


revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade():
    # ── user_id FK (nullable — not every contact has an account) ──
    op.add_column("advertiser_contacts",
                  sa.Column("user_id", sa.String(36), nullable=True))
    op.create_index("ix_adv_contacts_user_id", "advertiser_contacts", ["user_id"])
    op.create_foreign_key(
        "fk_adv_contacts_user",
        "advertiser_contacts", "users",
        ["user_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── title / role (optional, free-text) ──
    op.add_column("advertiser_contacts",
                  sa.Column("title", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("advertiser_contacts", "title")
    op.drop_constraint("fk_adv_contacts_user", "advertiser_contacts", type_="foreignkey")
    op.drop_index("ix_adv_contacts_user_id", table_name="advertiser_contacts")
    op.drop_column("advertiser_contacts", "user_id")

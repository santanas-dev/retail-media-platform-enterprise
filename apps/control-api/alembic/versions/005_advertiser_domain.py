"""Advertiser domain foundation — brands, contracts, contacts + RLS

Revision ID: 005
Revises: 004
Create Date: 2026-07-04

Phase 4.0b: Read-only advertiser domain tables with RLS protection.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# RLS SELECT policies — fail-closed, same pattern as 004
# ---------------------------------------------------------------------------

RLS_POLICY_TEMPLATE = """
CREATE POLICY {table}_rls_sel ON {table}
    FOR SELECT
    USING (
        COALESCE(
            NULLIF(current_setting('app.rmp_is_admin', true), ''),
            'false'
        )::bool = true
        OR advertiser_organization_id = ANY(
            COALESCE(
                string_to_array(
                    NULLIF(
                        current_setting('app.rmp_scope_advertiser_ids', true),
                        ''
                    ),
                    ','
                ),
                '{{}}'::text[]
            )
        )
    )
"""


def upgrade() -> None:
    # --- advertiser_brands ---
    op.create_table(
        "advertiser_brands",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advertiser_organization_id", sa.String(36),
                  sa.ForeignKey("advertiser_organizations.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_adv_brands_org_id", "advertiser_brands", ["advertiser_organization_id"])
    op.create_index("ix_adv_brands_code", "advertiser_brands", ["code"])
    op.create_unique_constraint("uq_adv_brand_code_per_org", "advertiser_brands",
                                ["advertiser_organization_id", "code"])

    op.execute("ALTER TABLE advertiser_brands ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE advertiser_brands FORCE ROW LEVEL SECURITY")
    op.execute(RLS_POLICY_TEMPLATE.format(table="advertiser_brands"))

    # --- advertiser_contracts ---
    op.create_table(
        "advertiser_contracts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advertiser_organization_id", sa.String(36),
                  sa.ForeignKey("advertiser_organizations.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contract_number", sa.String(128), nullable=True),
        sa.Column("budget_limit_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("budget_limit_currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("terms_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_adv_contracts_org_id", "advertiser_contracts", ["advertiser_organization_id"])
    op.create_index("ix_adv_contracts_code", "advertiser_contracts", ["code"])
    op.create_unique_constraint("uq_adv_contract_code_per_org", "advertiser_contracts",
                                ["advertiser_organization_id", "code"])

    op.execute("ALTER TABLE advertiser_contracts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE advertiser_contracts FORCE ROW LEVEL SECURITY")
    op.execute(RLS_POLICY_TEMPLATE.format(table="advertiser_contracts"))

    # --- advertiser_contacts ---
    op.create_table(
        "advertiser_contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advertiser_organization_id", sa.String(36),
                  sa.ForeignKey("advertiser_organizations.id"), nullable=False),
        sa.Column("contact_type", sa.String(32), nullable=False, server_default="primary"),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_adv_contacts_org_id", "advertiser_contacts", ["advertiser_organization_id"])
    op.create_index(
        "ix_adv_contacts_primary", "advertiser_contacts",
        ["advertiser_organization_id", "contact_type"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE AND status = 'active'"),
    )

    op.execute("ALTER TABLE advertiser_contacts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE advertiser_contacts FORCE ROW LEVEL SECURITY")
    op.execute(RLS_POLICY_TEMPLATE.format(table="advertiser_contacts"))


def downgrade() -> None:
    for table in ("advertiser_contacts", "advertiser_contracts", "advertiser_brands"):
        op.execute(f"DROP POLICY IF EXISTS {table}_rls_sel ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)

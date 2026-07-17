"""ADR-018-IMPL-001 — Multitenancy foundation: retailer_id + two-level RLS.

Revision ID: 020
Revises: 019
Create Date: 2026-07-17

Adds:
- retailers table
- retailer_id on 31 tenant-scoped tables
- default retailer + backfill
- two-level RLS (retailer + advertiser) for all previously RLS-protected tables
- RLS for tenant tables that lacked explicit policies
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── RLS helper expressions ────────────────────────────────────────────────────

_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)

_SCOPE_RETAILER = (
    "COALESCE(string_to_array("
    "NULLIF(current_setting('app.rmp_scope_retailer_ids', true), ''), "
    "','), '{}'::text[])"
)

_SCOPE_ADVERTISER = (
    "COALESCE(string_to_array("
    "NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''), "
    "','), '{}'::text[])"
)

# Two-level RLS: admin OR (retailer match AND advertiser match)
# For tables with both columns:
TWO_LEVEL = f"({_IS_ADMIN} OR (retailer_id = ANY({_SCOPE_RETAILER}) AND advertiser_organization_id = ANY({_SCOPE_ADVERTISER})))"

# For tables with retailer_id only (no advertiser FK — derive from parent):
RETAILER_ONLY = f"({_IS_ADMIN} OR retailer_id = ANY({_SCOPE_RETAILER}))"

# ── Tenant table list ─────────────────────────────────────────────────────────

# Tables with advertiser_organization_id → two-level RLS
ADVERTISER_TABLES = [
    "advertiser_brands",
    "advertiser_contacts",
    "advertiser_contracts",
    "advertiser_invites",
    "advertiser_user_memberships",
    "campaigns",
    "campaign_briefs",
    "creative_assets",
    "creative_upload_sessions",
]

# Tables derived from advertiser scope (via campaign/device hierarchy)
# These get retailer_id directly — RLS added where missing
DERIVED_TABLES = [
    "campaign_approvals",
    "campaign_creatives",
    "campaign_flights",
    "campaign_placements",
    "campaign_status_history",
    "delivery_manifests",
    "delivery_manifest_assets",
    "delivery_manifest_surfaces",
    "delivery_plans",
    "inventory_bookings",
    "pop_events_raw",
    "pop_ingestion_batches",
]

# Store/branch hierarchy tables — retailer scope only (no advertiser FK)
HIERARCHY_TABLES = [
    "branches",
    "clusters",
    "stores",
    "physical_devices",
    "display_surfaces",
    "inventory_rules",
    "inventory_slots",
]

ALL_TENANT = ADVERTISER_TABLES + DERIVED_TABLES + HIERARCHY_TABLES + [
    "advertiser_applications",  # special RLS (organization_id), but needs retailer_id
    "advertiser_organizations",  # special RLS (id), but needs retailer_id
]

DEFAULT_RETAILER_ID = "00000000-0000-4000-a000-000000000001"


def upgrade() -> None:
    # ── 1. Create retailers table ──
    op.create_table(
        "retailers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), unique=True, nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_retailers_code", "retailers", ["code"])
    op.create_index("ix_retailers_status", "retailers", ["status"])

    # ── 2. Add retailer_id (nullable) to all tenant tables ──
    for table in ALL_TENANT:
        op.execute(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS retailer_id VARCHAR(36)"
        )

    # ── 3. Insert default retailer ──
    op.execute(f"""
        INSERT INTO retailers (id, code, legal_name, display_name, status)
        VALUES ('{DEFAULT_RETAILER_ID}', 'default', 'Default Retailer', 'Default Retailer', 'active')
        ON CONFLICT (id) DO NOTHING
    """)

    # ── 4. Backfill retailer_id on all tenant tables ──
    for table in ALL_TENANT:
        op.execute(
            f"UPDATE {table} SET retailer_id = '{DEFAULT_RETAILER_ID}' WHERE retailer_id IS NULL"
        )

    # ── 5. SET NOT NULL ──
    for table in ALL_TENANT:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN retailer_id SET NOT NULL")

    # ── 6. FK constraints ──
    for table in ALL_TENANT:
        op.create_foreign_key(
            f"fk_{table}_retailer",
            table, "retailers",
            ["retailer_id"], ["id"],
        )

    # ── 7. Index on retailer_id for all tenant tables ──
    for table in ALL_TENANT:
        op.create_index(f"ix_{table}_retailer_id", table, ["retailer_id"])

    # ── 8. Two-level RLS: advertiser-scoped tables ──
    for table in ADVERTISER_TABLES:
        # Drop old single-level policies, create two-level
        for suffix, op_type in [("sel", "SELECT"), ("ins", "INSERT"), ("upd", "UPDATE"), ("del", "DELETE")]:
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        for op_type in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            suffix = {"SELECT": "sel", "INSERT": "ins", "UPDATE": "upd", "DELETE": "del"}[op_type]
            clause = "USING" if op_type == "SELECT" else ("WITH CHECK" if op_type == "INSERT" else "USING")
            if op_type == "UPDATE":
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        USING ({TWO_LEVEL})
                        WITH CHECK ({TWO_LEVEL});
                """)
            else:
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        {clause} ({TWO_LEVEL});
                """)

    # ── 8b. advertiser_applications uses organization_id (not advertiser_organization_id) ──
    APP_ORG_TWO_LEVEL = TWO_LEVEL.replace("advertiser_organization_id", "organization_id")
    for table in ["advertiser_applications"]:
        for suffix in ("sel", "ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        for op_type in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            suffix = {"SELECT": "sel", "INSERT": "ins", "UPDATE": "upd", "DELETE": "del"}[op_type]
            clause = "USING" if op_type == "SELECT" else ("WITH CHECK" if op_type == "INSERT" else "USING")
            if op_type == "UPDATE":
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        USING ({APP_ORG_TWO_LEVEL})
                        WITH CHECK ({APP_ORG_TWO_LEVEL});
                """)
            else:
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        {clause} ({APP_ORG_TWO_LEVEL});
                """)

    # ── 8c. advertiser_organizations uses id (IS the org, not FK) ──
    ADO_TWO_LEVEL = TWO_LEVEL.replace("advertiser_organization_id", "id")
    for table in ["advertiser_organizations"]:
        for suffix in ("sel", "ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        for op_type in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            suffix = {"SELECT": "sel", "INSERT": "ins", "UPDATE": "upd", "DELETE": "del"}[op_type]
            clause = "USING" if op_type == "SELECT" else ("WITH CHECK" if op_type == "INSERT" else "USING")
            if op_type == "UPDATE":
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        USING ({ADO_TWO_LEVEL})
                        WITH CHECK ({ADO_TWO_LEVEL});
                """)
            else:
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        {clause} ({ADO_TWO_LEVEL});
                """)

    # ── 9. RLS for derived tables (no advertiser FK, retailer scope only) ──
    for table in DERIVED_TABLES:
        for suffix in ("sel", "ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        for op_type in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            suffix = {"SELECT": "sel", "INSERT": "ins", "UPDATE": "upd", "DELETE": "del"}[op_type]
            clause = "USING" if op_type == "SELECT" else ("WITH CHECK" if op_type == "INSERT" else "USING")
            if op_type == "UPDATE":
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        USING ({RETAILER_ONLY})
                        WITH CHECK ({RETAILER_ONLY});
                """)
            else:
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        {clause} ({RETAILER_ONLY});
                """)

    # ── 10. RLS for hierarchy tables (branches, stores, etc.) ──
    for table in HIERARCHY_TABLES:
        for suffix in ("sel", "ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        for op_type in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            suffix = {"SELECT": "sel", "INSERT": "ins", "UPDATE": "upd", "DELETE": "del"}[op_type]
            clause = "USING" if op_type == "SELECT" else ("WITH CHECK" if op_type == "INSERT" else "USING")
            if op_type == "UPDATE":
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        USING ({RETAILER_ONLY})
                        WITH CHECK ({RETAILER_ONLY});
                """)
            else:
                op.execute(f"""
                    CREATE POLICY {table}_rls_{suffix} ON {table}
                        FOR {op_type}
                        {clause} ({RETAILER_ONLY});
                """)


def downgrade() -> None:
    # Drop RLS policies
    for table in ALL_TENANT:
        for suffix in ("sel", "ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")

    # Drop FKs and columns
    for table in ALL_TENANT:
        op.drop_constraint(f"fk_{table}_retailer", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_retailer_id", table_name=table)
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS retailer_id")

    # Drop retailers table
    op.execute("DROP TABLE IF EXISTS retailers CASCADE")

"""EPIC-L-SEAT-LEDGER-001A1 — License seat ledger foundation tables + RLS.

Revision ID: 034
Revises: 033
Create Date: 2026-08-20

Adds:
  license_grants — operator/installation license grants (single effective grant)
  license_seats  — per-device seat reservations (open/historical intervals)

Design freeze (docs/architecture/epic-l-licensing.md §"Layer 1 Seat Ledger
Design Freeze") is authoritative. Key invariants encoded at DB level:

license_grants:
  - source restricted to 'dev-ingest' in Layer 1 (no signed upload yet)
  - max_devices / overage_allowance / grace_days non-negative
  - valid_until >= valid_from when valid_until set
  - status ('current'|'revoked'|'superseded') is separate from the computed
    active/grace/expired lifetime; partial unique index allows at most ONE
    current grant per installation (single effective grant invariant)
  - expired/grace are NOT stored — computed from dates at read time

license_seats:
  - one open seat (released_at IS NULL) per device — partial unique index
  - released_at >= reserved_at
  - historical reserve/release intervals preserved (no delete-on-release)
  - FK behavior is RESTRICT (NO ACTION): deleting a grant or device that still
    has seat history fails — matches the audit-history pattern used elsewhere
    (device_status_history, campaign_status_history use plain FK = NO ACTION)

RLS:
  - ENABLE + FORCE ROW LEVEL SECURITY on both tables
  - operator/service scope: rows visible/writable only when the server has set
    app.rmp_is_admin = true. advertiser scope is NOT consulted.
  - owner role is used only for migrations/test fixtures (as everywhere else).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "034"
down_revision: Union[str, None] = "033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# RLS: only admin context (operator/service scope). No advertiser scope.
_IS_ADMIN = (
    "COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), "
    "'false')::bool = true"
)


def _apply_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY {table}_rls_sel ON {table}
            FOR SELECT
            USING ({_IS_ADMIN});
    """)
    op.execute(f"""
        CREATE POLICY {table}_rls_ins ON {table}
            FOR INSERT
            WITH CHECK ({_IS_ADMIN});
    """)
    op.execute(f"""
        CREATE POLICY {table}_rls_upd ON {table}
            FOR UPDATE
            USING ({_IS_ADMIN})
            WITH CHECK ({_IS_ADMIN});
    """)
    op.execute(f"""
        CREATE POLICY {table}_rls_del ON {table}
            FOR DELETE
            USING ({_IS_ADMIN});
    """)


def upgrade() -> None:
    # ── license_grants ──
    op.create_table(
        "license_grants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("license_id", sa.String(128), nullable=False, unique=True),
        sa.Column("licensee_id", sa.String(128), nullable=False),
        sa.Column("licensee_name", sa.String(255), nullable=False),
        sa.Column("tier", sa.String(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_devices", sa.Integer, nullable=False, server_default="0"),
        sa.Column("overage_allowance", sa.Integer, nullable=False, server_default="0"),
        sa.Column("grace_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("features", postgresql.JSONB, nullable=True),
        sa.Column("installation_binding", sa.String(255), nullable=True),
        sa.Column("nonce", sa.String(255), nullable=True),
        sa.Column("schema_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("kid", sa.String(255), nullable=True),
        sa.Column(
            "source", sa.String(32), nullable=False, server_default="dev-ingest",
        ),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="current",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint("max_devices >= 0", name="ck_license_grants_max_devices_nonneg"),
        sa.CheckConstraint("overage_allowance >= 0", name="ck_license_grants_overage_nonneg"),
        sa.CheckConstraint("grace_days >= 0", name="ck_license_grants_grace_nonneg"),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_license_grants_valid_window",
        ),
        sa.CheckConstraint(
            "source IN ('dev-ingest')",
            name="ck_license_grants_source_layer1",
        ),
        sa.CheckConstraint(
            "status IN ('current', 'revoked', 'superseded')",
            name="ck_license_grants_status",
        ),
    )
    op.create_index("ix_license_grants_status", "license_grants", ["status"])
    op.create_index("ix_license_grants_licensee", "license_grants", ["licensee_id"])

    # At most one current/effective grant per installation.
    op.execute("""
        CREATE UNIQUE INDEX uq_license_grants_single_current ON license_grants ((1))
        WHERE status = 'current'
    """)

    # ── license_seats ──
    op.create_table(
        "license_seats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "license_id", sa.String(36),
            sa.ForeignKey("license_grants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "device_id", sa.String(36),
            sa.ForeignKey("physical_devices.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "released_at IS NULL OR released_at >= reserved_at",
            name="ck_license_seats_release_after_reserve",
        ),
    )
    op.create_index("ix_license_seats_license", "license_seats", ["license_id"])
    op.create_index("ix_license_seats_device", "license_seats", ["device_id"])

    # At most one open (unreleased) seat per device.
    op.execute("""
        CREATE UNIQUE INDEX uq_license_seats_open_per_device ON license_seats (device_id)
        WHERE released_at IS NULL
    """)

    # ── RLS ──
    _apply_rls("license_grants")
    _apply_rls("license_seats")


def downgrade() -> None:
    for table in ("license_seats", "license_grants"):
        for suffix in ("sel", "ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_rls_{suffix} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.drop_table("license_seats")
    op.drop_table("license_grants")

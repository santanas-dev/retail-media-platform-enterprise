"""032: Commerce Contour 2 foundation tables (COMMERCE-CONTUR2-001A1).

Adds four MVP tables:
  commerce_tariff_versions — pricing container with validity window
  commerce_price_items     — per-surface price inside a tariff version
  commerce_orders          — advertiser purchases inventory
  commerce_order_lines     — line items in a commerce order
"""

from alembic import op
import sqlalchemy as sa


revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade():
    # ── commerce_tariff_versions ──
    op.create_table(
        "commerce_tariff_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("valid_to", sa.Date, nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_commerce_tariff_versions_status", "commerce_tariff_versions",
                    ["status"])
    op.create_index("ix_commerce_tariff_versions_valid", "commerce_tariff_versions",
                    ["valid_from", "valid_to"])

    # ── commerce_price_items ──
    op.create_table(
        "commerce_price_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tariff_version_id", sa.String(36), nullable=False),
        sa.Column("surface_id", sa.String(36), nullable=False),
        sa.Column("billing_unit", sa.String(32), nullable=False,
                  server_default="surface_day"),
        sa.Column("unit_price_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_commerce_price_items_tariff", "commerce_price_items",
                    ["tariff_version_id"])
    op.create_unique_constraint("uq_price_item_tariff_surface", "commerce_price_items",
                                ["tariff_version_id", "surface_id"])
    op.create_foreign_key(
        "fk_price_item_tariff_version", "commerce_price_items",
        "commerce_tariff_versions", ["tariff_version_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_price_item_surface", "commerce_price_items",
        "display_surfaces", ["surface_id"], ["id"],
    )

    # ── commerce_orders ──
    op.create_table(
        "commerce_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advertiser_organization_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("payment_status", sa.String(32), nullable=False,
                  server_default="not_required"),
        sa.Column("tariff_version_id", sa.String(36), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_commerce_orders_org", "commerce_orders",
                    ["advertiser_organization_id"])
    op.create_index("ix_commerce_orders_status", "commerce_orders", ["status"])
    op.create_foreign_key(
        "fk_commerce_order_org", "commerce_orders",
        "advertiser_organizations", ["advertiser_organization_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_commerce_order_tariff", "commerce_orders",
        "commerce_tariff_versions", ["tariff_version_id"], ["id"],
    )

    # ── commerce_order_lines ──
    op.create_table(
        "commerce_order_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("surface_id", sa.String(36), nullable=False),
        sa.Column("date_from", sa.Date, nullable=False),
        sa.Column("date_to", sa.Date, nullable=False),
        sa.Column("quantity_days", sa.Integer, nullable=False),
        sa.Column("unit_price_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_commerce_order_lines_order", "commerce_order_lines",
                    ["order_id"])
    op.create_foreign_key(
        "fk_order_line_order", "commerce_order_lines",
        "commerce_orders", ["order_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_order_line_surface", "commerce_order_lines",
        "display_surfaces", ["surface_id"], ["id"],
    )


def downgrade():
    op.drop_table("commerce_order_lines")
    op.drop_table("commerce_orders")
    op.drop_table("commerce_price_items")
    op.drop_table("commerce_tariff_versions")

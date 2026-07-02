"""${message}

Revision ID: 002
Revises: 001
Create Date: 2026-07-02

Phase 2.1: Identity/RBAC/RLS/Audit foundation tables.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # Users
    # -----------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("auth_provider", sa.String(32), nullable=False, server_default="local"),
        sa.Column("external_subject", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("is_break_glass", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # Roles
    # -----------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # Permissions
    # -----------------------------------------------------------------------
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(128), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # Role ↔ Permission (M:N)
    # -----------------------------------------------------------------------
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"), nullable=False, index=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id"),
                  nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    # -----------------------------------------------------------------------
    # User ↔ Role (M:N with optional scope)
    # -----------------------------------------------------------------------
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"), nullable=False, index=True),
        sa.Column("scope_type", sa.String(32), nullable=True),
        sa.Column("scope_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("(scope_type IS NULL) = (scope_id IS NULL)",
                           name="ck_user_role_scope_pair"),
        sa.UniqueConstraint("user_id", "role_id", "scope_type", "scope_id",
                            name="uq_user_role_scoped"),
    )
    # Partial unique index: prevent duplicate unscoped (global) role assignments
    # PostgreSQL treats NULLs as distinct in unique constraints, so a
    # separate partial index is needed for the (scope_type IS NULL) case.
    op.create_index(
        "uq_user_role_unscoped", "user_roles",
        ["user_id", "role_id"],
        unique=True,
        postgresql_where=sa.text("scope_type IS NULL AND scope_id IS NULL"),
    )

    # -----------------------------------------------------------------------
    # Access Scopes (RLS foundation)
    # -----------------------------------------------------------------------
    op.create_table(
        "access_scopes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("branch_id", sa.String(36), sa.ForeignKey("branches.id"),
                  nullable=True, index=True),
        sa.Column("cluster_id", sa.String(36), sa.ForeignKey("clusters.id"),
                  nullable=True, index=True),
        sa.Column("store_id", sa.String(36), sa.ForeignKey("stores.id"),
                  nullable=True, index=True),
        sa.Column("advertiser_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # -----------------------------------------------------------------------
    # User ↔ Access Scope (M:N)
    # -----------------------------------------------------------------------
    op.create_table(
        "user_access_scopes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("access_scope_id", sa.String(36), sa.ForeignKey("access_scopes.id"),
                  nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "access_scope_id", name="uq_user_access_scope"),
    )

    # -----------------------------------------------------------------------
    # Audit Events (operational)
    # -----------------------------------------------------------------------
    op.create_table(
        "audit_events_operational",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"),
                  nullable=True, index=True),
        sa.Column("action", sa.String(128), nullable=False, index=True),
        sa.Column("target_type", sa.String(64), nullable=False, index=True),
        sa.Column("target_id", sa.String(36), nullable=True, index=True),
        sa.Column("correlation_id", sa.String(64), nullable=True, index=True),
        sa.Column("ip_address", sa.String(45), nullable=False, server_default=""),
        sa.Column("details_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_index("uq_user_role_unscoped", table_name="user_roles")
    op.drop_table("audit_events_operational")
    op.drop_table("user_access_scopes")
    op.drop_table("access_scopes")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")

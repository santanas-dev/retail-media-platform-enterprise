"""030: Add file metadata to advertiser_contracts + contract_upload_sessions table.

Supports PDF upload for advertiser contracts (ADVERTISER-UX-001B2).
File columns are nullable — existing contracts without files remain valid.
Upload sessions table mirrors creative_upload_sessions pattern but scoped to contracts.
"""

from alembic import op
import sqlalchemy as sa


revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade():
    # ── File metadata columns on advertiser_contracts ──
    op.add_column("advertiser_contracts",
                  sa.Column("file_storage_key", sa.String(512), nullable=True))
    op.add_column("advertiser_contracts",
                  sa.Column("file_name", sa.String(255), nullable=True))
    op.add_column("advertiser_contracts",
                  sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("advertiser_contracts",
                  sa.Column("file_sha256", sa.String(64), nullable=True))
    op.add_column("advertiser_contracts",
                  sa.Column("file_content_type", sa.String(64), nullable=True))
    op.add_column("advertiser_contracts",
                  sa.Column("file_uploaded_at", sa.DateTime(timezone=True), nullable=True))

    # ── Contract upload sessions table ──
    op.create_table(
        "contract_upload_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("contract_id",
                  sa.String(36), sa.ForeignKey("advertiser_contracts.id"),
                  nullable=False, index=True),
        sa.Column("advertiser_organization_id",
                  sa.String(36), sa.ForeignKey("advertiser_organizations.id"),
                  nullable=False, index=True),
        sa.Column("storage_bucket", sa.String(128), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("content_length", sa.BigInteger(), nullable=False),
        sa.Column("sha256_checksum", sa.String(64), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # RLS for contract upload sessions — same pattern as creative_upload_sessions (013)
    op.execute(sa.text("""
        ALTER TABLE contract_upload_sessions ENABLE ROW LEVEL SECURITY;
    """))
    op.execute(sa.text("""
        CREATE POLICY contract_upload_sessions_rls_sel ON contract_upload_sessions
            FOR SELECT
            USING (
                COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), 'false')::bool = true
                OR advertiser_organization_id = ANY(
                    COALESCE(
                        string_to_array(NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''), ','),
                        ARRAY[]::text[]
                    )
                )
            );
    """))
    op.execute(sa.text("""
        CREATE POLICY contract_upload_sessions_rls_ins ON contract_upload_sessions
            FOR INSERT
            WITH CHECK (
                COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), 'false')::bool = true
                OR advertiser_organization_id = ANY(
                    COALESCE(
                        string_to_array(NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''), ','),
                        ARRAY[]::text[]
                    )
                )
            );
    """))
    op.execute(sa.text("""
        CREATE POLICY contract_upload_sessions_rls_upd ON contract_upload_sessions
            FOR UPDATE
            USING (
                COALESCE(NULLIF(current_setting('app.rmp_is_admin', true), ''), 'false')::bool = true
                OR advertiser_organization_id = ANY(
                    COALESCE(
                        string_to_array(NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''), ','),
                        ARRAY[]::text[]
                    )
                )
            );
    """))


def downgrade():
    op.execute(sa.text("DROP POLICY IF EXISTS contract_upload_sessions_org_isolation ON contract_upload_sessions;"))
    op.drop_table("contract_upload_sessions")
    op.drop_column("advertiser_contracts", "file_uploaded_at")
    op.drop_column("advertiser_contracts", "file_content_type")
    op.drop_column("advertiser_contracts", "file_sha256")
    op.drop_column("advertiser_contracts", "file_size_bytes")
    op.drop_column("advertiser_contracts", "file_name")
    op.drop_column("advertiser_contracts", "file_storage_key")

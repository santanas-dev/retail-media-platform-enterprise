"""Creative upload sessions RLS (S-035h)

Revision ID: 013
Revises: 012
Create Date: 2026-07-12

Adds row-level security to creative_upload_sessions so that
upload sessions are scoped to the advertiser organization.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RLS_DIRECT = """
CREATE POLICY creative_upload_sessions_rls_sel ON creative_upload_sessions
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
                ARRAY[]::text[]
            )
        )
    )
"""

RLS_INSERT = """
CREATE POLICY creative_upload_sessions_rls_ins ON creative_upload_sessions
    FOR INSERT
    WITH CHECK (
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
                ARRAY[]::text[]
            )
        )
    )
"""

RLS_UPDATE = """
CREATE POLICY creative_upload_sessions_rls_upd ON creative_upload_sessions
    FOR UPDATE
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
                ARRAY[]::text[]
            )
        )
    )
"""


def upgrade() -> None:
    op.execute("ALTER TABLE creative_upload_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE creative_upload_sessions FORCE ROW LEVEL SECURITY")
    op.execute(RLS_DIRECT)
    op.execute(RLS_INSERT)
    op.execute(RLS_UPDATE)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS creative_upload_sessions_rls_sel ON creative_upload_sessions")
    op.execute("DROP POLICY IF EXISTS creative_upload_sessions_rls_ins ON creative_upload_sessions")
    op.execute("DROP POLICY IF EXISTS creative_upload_sessions_rls_upd ON creative_upload_sessions")

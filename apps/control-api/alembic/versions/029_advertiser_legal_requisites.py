"""029: Add legal requisites columns to advertiser_organizations.

All columns are nullable to preserve existing orgs without requisites.
API validation enforces required fields when creating/updating requisites.
Checksum validation is deferred technical debt, NOT blocking in A1.
"""

from alembic import op
import sqlalchemy as sa

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("advertiser_organizations", sa.Column("legal_entity_type", sa.String(32), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("legal_form", sa.String(32), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("legal_form_other", sa.String(255), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("inn", sa.String(32), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("legal_address", sa.Text, nullable=True))
    op.add_column("advertiser_organizations", sa.Column("settlement_account", sa.String(32), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("correspondent_account", sa.String(32), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("bik", sa.String(16), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("bank_name", sa.String(255), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("kpp", sa.String(16), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("ogrn", sa.String(32), nullable=True))
    op.add_column("advertiser_organizations", sa.Column("ogrnip", sa.String(32), nullable=True))


def downgrade():
    op.drop_column("advertiser_organizations", "ogrnip")
    op.drop_column("advertiser_organizations", "ogrn")
    op.drop_column("advertiser_organizations", "kpp")
    op.drop_column("advertiser_organizations", "bank_name")
    op.drop_column("advertiser_organizations", "bik")
    op.drop_column("advertiser_organizations", "correspondent_account")
    op.drop_column("advertiser_organizations", "settlement_account")
    op.drop_column("advertiser_organizations", "legal_address")
    op.drop_column("advertiser_organizations", "inn")
    op.drop_column("advertiser_organizations", "legal_form_other")
    op.drop_column("advertiser_organizations", "legal_form")
    op.drop_column("advertiser_organizations", "legal_entity_type")

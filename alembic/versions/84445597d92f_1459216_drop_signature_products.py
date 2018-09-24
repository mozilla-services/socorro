"""1459216 drop signature_products and signature_products_rollup tables

Revision ID: 84445597d92f
Revises: f355b5458f82
Create Date: 2018-09-24 18:54:53.315200

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '84445597d92f'
down_revision = 'f355b5458f82'


def upgrade():
    op.execute('DROP TABLE IF EXISTS signature_products')
    op.execute('DROP TABLE IF EXISTS signature_products_rollup')


def downgrade():
    # No downgrade
    pass

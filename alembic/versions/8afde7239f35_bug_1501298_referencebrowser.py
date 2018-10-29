"""bug 1501298 referencebrowser

Revision ID: 8afde7239f35
Revises: 84445597d92f
Create Date: 2018-10-29 14:40:33.767066

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '8afde7239f35'
down_revision = '84445597d92f'


def upgrade():
    op.execute("""
        INSERT INTO products
        (product_name, sort, release_name, rapid_beta_version, rapid_release_version)
        VALUES
        ('ReferenceBrowser', 11, 'referencebrowser', 1.0, 1.0)
    """)


def downgrade():
    op.execute("""
        DELETE FROM products
        WHERE product_name = 'ReferenceBrowser'
    """)

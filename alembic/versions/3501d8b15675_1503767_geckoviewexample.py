"""1503767 geckoviewexample - add GeckoViewExample catchall product

Revision ID: 3501d8b15675
Revises: 8afde7239f35
Create Date: 2018-11-01 15:37:38.264250

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '3501d8b15675'
down_revision = '8afde7239f35'


def upgrade():
    op.execute("""
        INSERT INTO products
        (product_name, sort, release_name, rapid_beta_version, rapid_release_version)
        VALUES
        ('GeckoViewExample', 11, 'geckoviewexample', 1.0, 1.0)
    """)


def downgrade():
    op.execute("""
        DELETE FROM products
        WHERE product_name = 'GeckoViewExample'
    """)

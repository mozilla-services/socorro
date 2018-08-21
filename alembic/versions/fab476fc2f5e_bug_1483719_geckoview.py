"""bug 1483719 geckoview - add GeckoView catchall product

Revision ID: fab476fc2f5e
Revises: b8da3a85f665
Create Date: 2018-08-21 15:03:31.778855

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'fab476fc2f5e'
down_revision = 'b8da3a85f665'


def upgrade():
    op.execute("""
        INSERT INTO products
        (product_name, sort, release_name, rapid_beta_version, rapid_release_version)
        VALUES
        ('GeckoView', 10, 'geckoview', 1.0, 1.0)
    """)


def downgrade():
    op.execute("""
        DELETE FROM products
        WHERE product_name = 'GeckoView'
    """)

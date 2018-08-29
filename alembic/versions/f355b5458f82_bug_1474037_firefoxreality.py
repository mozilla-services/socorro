"""bug 1474037: add FirefoxReality

Revision ID: f355b5458f82
Revises: fab476fc2f5e
Create Date: 2018-08-29 13:51:49.319243

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'f355b5458f82'
down_revision = 'fab476fc2f5e'


PRODUCTNAME = 'FirefoxReality'
SORT = 4


def upgrade():
    op.execute("""
        INSERT INTO products
        (product_name, sort, release_name, rapid_beta_version, rapid_release_version)
        VALUES
        ('%s', %s, '%s', 1.0, 1.0)
    """ % (PRODUCTNAME, SORT, PRODUCTNAME.lower()))


def downgrade():
    op.execute("""
        DELETE FROM products
        WHERE product_name = '%s'
    """ % (PRODUCTNAME,))

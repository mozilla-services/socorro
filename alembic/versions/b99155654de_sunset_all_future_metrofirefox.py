"""sunset all future MetroFirefox

Revision ID: b99155654de
Revises: 56f5cdf9bcdb
Create Date: 2015-07-31 15:51:26.282796

"""

# revision identifiers, used by Alembic.
revision = 'b99155654de'
down_revision = '56f5cdf9bcdb'

from alembic import op
from socorrolib.lib.migrations import load_stored_proc


def upgrade():
    op.execute("""
        UPDATE product_versions
        SET sunset_date = NOW()
        WHERE
            product_name = 'MetroFirefox' AND
            sunset_date >= NOW()
    """)
    load_stored_proc(op, ['update_product_versions.sql'])


def downgrade():
    load_stored_proc(op, ['update_product_versions.sql'])

"""bug 928051 - add b2g to reports_clean

Revision ID: 74d6fd90b59
Revises: c1ac31c8fea
Create Date: 2014-02-18 12:53:41.577292

"""

# revision identifiers, used by Alembic.
revision = '74d6fd90b59'
down_revision = 'c1ac31c8fea'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['001_update_reports_clean.sql', 'update_product_versions.sql'])
    op.alter_column(u'update_channel_map', u'update_channel', type_=sa.CITEXT())
    op.alter_column(u'raw_update_channels', u'update_channel',
                    type_=sa.CITEXT())
    op.execute("""
        INSERT INTO product_release_channels VALUES ('B2G', 'Release', 1)
        WHERE NOT EXISTS (
            SELECT product_name, release_channel FROM product_release_channels
            WHERE product_name = 'B2G'
            AND release_channel = 'Release'
        )
    """)
    op.execute(""" COMMIT """)


def downgrade():
    load_stored_proc(op, ['001_update_reports_clean.sql', 'update_product_versions.sql'])
    op.alter_column(u'update_channel_map', u'update_channel', type_=sa.TEXT())
    op.alter_column(u'raw_update_channels', u'update_channel', type_=sa.TEXT())

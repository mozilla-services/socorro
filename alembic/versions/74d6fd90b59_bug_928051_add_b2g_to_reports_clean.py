"""bug 928051 - add b2g to reports_clean

Revision ID: 74d6fd90b59
Revises: 2580b5b6b7aa
Create Date: 2014-02-18 12:53:41.577292

"""

# revision identifiers, used by Alembic.
revision = '74d6fd90b59'
down_revision = '2580b5b6b7aa'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['001_update_reports_clean.sql', 'update_product_versions.sql'])
    op.alter_column(u'update_channel_map', u'update_channel',
                    type_=citexttype.CitextType())
    op.alter_column(u'raw_update_channels', u'update_channel',
                    type_=citexttype.CitextType())
    op.execute("""
        INSERT INTO product_release_channels SELECT ('B2G', 'Release', 1)
        WHERE NOT EXISTS (
            SELECT product_name, release_channel FROM product_release_channels
            WHERE product_name = 'B2G'
            AND release_channel = 'Release'
        )
    """)

    op.execute("""
        TRUNCATE update_channel_map
    """)

    op.execute("""
        INSERT INTO update_channel_map
        (update_channel, productid, version_field, rewrite)
        VALUES
        ('nightly',
         '{3c2e2abc-06d4-11e1-ac3b-374f68613e61}',
         'B2G_OS_Version',
         '{"Android_Manufacturer": "ZTE",
           "Android_Model": "roamer2",
           "Android_Version": "15(REL)",
           "B2G_OS_Version": "1.0.1.0-prerelease",
           "BuildID":
                ["20130621133927", "20130621152332",
                 "20130531232151", "20130617105829",
                 "20130724040538"],
            "ProductName": "B2G",
            "ReleaseChannel": "nightly",
            "Version": "18.0",
            "rewrite_update_channel_to": "release-zte",
            "rewrite_build_type_to": "release"}'
        )
    """)
    op.execute(""" COMMIT """)


def downgrade():
    load_stored_proc(op, ['001_update_reports_clean.sql', 'update_product_versions.sql'])
    op.alter_column(u'update_channel_map', u'update_channel', type_=sa.TEXT())
    op.alter_column(u'raw_update_channels', u'update_channel', type_=sa.TEXT())

"""Fixes bug 968493 Adds raw_update_channel and co.

Revision ID: 4d8345089e2a
Revises: 131b277f5ef7
Create Date: 2014-02-11 07:25:13.733392

"""

# revision identifiers, used by Alembic.
revision = '4d8345089e2a'
down_revision = '131b277f5ef7'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(u'raw_update_channels',
        sa.Column(u'update_channel', sa.TEXT(), nullable=False),
        sa.Column(u'product_name', sa.TEXT(), nullable=False),
        sa.Column(u'version', sa.TEXT(), nullable=False),
        sa.Column(u'build', sa.NUMERIC(), nullable=False),
        sa.Column(u'first_report', postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(u'update_channel', u'product_name', u'version', u'build')
    )
    fix_permissions(op, 'raw_update_channels')

    op.create_table(u'update_channel_map',
        sa.Column(u'update_channel', sa.TEXT(), nullable=False),
        sa.Column(u'productid', sa.TEXT(), nullable=False),
        sa.Column(u'version_field', sa.TEXT(), nullable=False),
        sa.Column(u'rewrite', jsontype.JsonType(), nullable=False),
        sa.PrimaryKeyConstraint(u'update_channel', u'productid', u'version_field')
    )
    fix_permissions(op, 'update_channel_map')

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
            "rewrite_to": "release-zte"}'
        )
    """)

    # nothing depends on this yet in stored procs
    op.add_column(u'reports_clean', sa.Column(u'update_channel', sa.TEXT(), nullable=True))

    load_stored_proc(op, ['update_raw_update_channel.sql',
                          'backfill_raw_update_channel.sql',
                          'backfill_matviews.sql'])


def downgrade():
    op.drop_column(u'reports_clean', u'update_channel')
    op.drop_table(u'update_channel_map')
    op.drop_table(u'raw_update_channels')

    op.execute(""" DROP FUNCTION backfill_raw_update_channel(timestamptz, timestamptz) """)
    op.execute(""" DROP FUNCTION update_raw_update_channel(timestamptz, interval, boolean, boolean, text) """)
    load_stored_proc(op, ['backfill_matviews.sql'])


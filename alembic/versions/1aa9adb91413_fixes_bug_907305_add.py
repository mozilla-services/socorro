"""Fixes bug 907305 - Add processed_crashes

Revision ID: 1aa9adb91413
Revises: 4d8345089e2a
Create Date: 2014-02-12 11:35:48.115591

"""

# revision identifiers, used by Alembic.
revision = '1aa9adb91413'
down_revision = '4d8345089e2a'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(u'processed_crashes',
        sa.Column(u'uuid', postgresql.UUID(), nullable=False),
        sa.Column(u'processed_crash', jsontype.JsonType, nullable=False),
        sa.Column(u'date_processed', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint()
    )

    op.execute("""
        INSERT INTO report_partition_info
            (table_name, build_order, keys, indexes, fkeys, partition_column, timetype)
        VALUES
            ('processed_crashes', '12', '{uuid}', '{date_processed}', '{}',
             'date_processed', 'TIMESTAMPTZ')
    """)


def downgrade():
    op.drop_table(u'processed_crashes')

    op.execute(""" DELETE FROM report_partition_info where table_name = 'processed_crashes' """)

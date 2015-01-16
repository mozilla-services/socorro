"""Fixes bug 794549 - add partitioning to reports_duplicates

Revision ID: 445fefe2e08f
Revises: 5387d590bc45
Create Date: 2015-01-15 15:34:05.435396

"""

# revision identifiers, used by Alembic.
revision = '445fefe2e08f'
down_revision = '5387d590bc45'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    # add entry to report_partition_info to start partitioning reports_duplicates
    # existing 'drop old partitions' crontabber will pick this up
    op.execute("""
        WITH bo AS (
            SELECT COALESCE(max(build_order) + 1, 1) as number
            FROM report_partition_info
        )
        INSERT into report_partition_info
        (table_name, build_order, keys, indexes, fkeys, partition_column, timetype)
            SELECT 'reports_duplicates', bo.number, '{uuid}',
             '{"date_processed, uuid"}', '{}', 'date_processed', 'TIMESTAMPTZ'
             FROM bo
     """)


def downgrade():
    op.execute("""
        DELETE from report_partition_info
        WHERE table_name = 'reports_duplicates'
    """)

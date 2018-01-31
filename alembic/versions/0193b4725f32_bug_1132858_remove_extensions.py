"""bug 1132858 remove extensions table

Revision ID: 0193b4725f32
Revises: bb8cdbb8a6bd
Create Date: 2018-01-31 14:21:41.032179

"""

# revision identifiers, used by Alembic.
revision = '0193b4725f32'
down_revision = 'bb8cdbb8a6bd'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    # Get a list of ALL tables that start with 'extensions_*' and drop them
    connection = op.get_bind()
    cursor = connection.connection.cursor()
    cursor.execute("""
        SELECT c.relname FROM pg_catalog.pg_class c
        WHERE c.relkind = 'r' AND c.relname LIKE 'extensions_%'
    """)
    all_table_names = []
    for records in cursor.fetchall():
        table_name, = records
        all_table_names.append(table_name)

    all_table_names.sort(reverse=True)
    for table_name in all_table_names:
        op.execute('DROP TABLE IF EXISTS {}'.format(table_name))

    # Now drop the extensions table itself
    op.execute('DROP TABLE IF EXISTS extensions')

    # Now remove the entry from report_partition_info so the crontabber job
    # doesn't try to create a new partition
    op.execute("""
        DELETE FROM report_partition_info WHERE table_name = 'extensions'
    """)

def downgrade():
    # There is no going back.
    pass

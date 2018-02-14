"""bug 1434930 missing symbols

Revision ID: dfead656fe89
Revises: 1feab2fbed4c
Create Date: 2018-02-14 17:49:19.481892

"""

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = 'dfead656fe89'
down_revision = '1feab2fbed4c'


def upgrade():
    # Get a list of ALL tables that start with 'missing_symbols'
    connection = op.get_bind()
    cursor = connection.connection.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name like 'missing_symbols%'
    """)
    all_table_names = []
    for records in cursor.fetchall():
        all_table_names.append(records[0])

    # Sort table names so "missing_symbols" is last since the others depend on it
    # and delete them in that order
    all_table_names.sort(reverse=True)
    for table_name in all_table_names:
        op.execute('DROP TABLE IF EXISTS {}'.format(table_name))

    # Now remove the entry from report_partition_info so the crontabber job
    # doesn't try to create a new partition
    op.execute("""
        DELETE FROM report_partition_info WHERE table_name = 'missing_symbols'
    """)


def downgrade():
    # No going back.
    pass

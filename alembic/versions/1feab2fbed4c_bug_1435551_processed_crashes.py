"""bug 1435551 processed_crashes

Revision ID: 1feab2fbed4c
Revises: 3c5d40ea7c5a
Create Date: 2018-02-09 21:05:12.020449

"""

from alembic import op
from socorro.lib.migrations import load_stored_proc

# revision identifiers, used by Alembic.
revision = '1feab2fbed4c'
down_revision = '3c5d40ea7c5a'


def upgrade():
    # Get a list of ALL tables that start with 'processed_crashes'
    connection = op.get_bind()
    cursor = connection.connection.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name like 'processed_crashes%'
    """)
    all_table_names = []
    for records in cursor.fetchall():
        all_table_names.append(records[0])

    # Sort table names so 'processed_crashes' is last since the others depend
    # on it and delete them in that order
    all_table_names.sort(reverse=True)
    for table_name in all_table_names:
        op.execute('DROP TABLE IF EXISTS {}'.format(table_name))

    # Now remove the entry from report_partition_info so the crontabber job
    # doesn't try to create a new partition
    op.execute("""
        DELETE FROM report_partition_info WHERE table_name = 'processed_crashes'
    """)

    # Now update the stored procedure
    load_stored_proc(op, ['truncate_partitions.sql'])


def downgrade():
    # No going back
    pass

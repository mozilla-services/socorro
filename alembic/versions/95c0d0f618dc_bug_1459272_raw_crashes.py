"""bug 1459272 raw crashes

Revision ID: 95c0d0f618dc
Revises: 68b29ca0e06d
Create Date: 2018-05-11 19:41:42.743352

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '95c0d0f618dc'
down_revision = '68b29ca0e06d'


def upgrade():
    # Delete the truncate_partitions stored procedure since the only thing
    # it was truncating was raw_crashes.
    op.execute('DROP FUNCTION IF EXISTS truncate_partitions(integer)')

    # Get rid of all tables that start with 'raw_crashes'
    connection = op.get_bind()
    cursor = connection.connection.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name like 'raw_crashes%'
    """)
    all_table_names = []
    for records in cursor.fetchall():
        all_table_names.append(records[0])

    # Sort table names so 'raw_crashes' is last since the others depend on it
    # and delete them in that order
    all_table_names.sort(reverse=True)
    for table_name in all_table_names:
        op.execute('DROP TABLE IF EXISTS {}'.format(table_name))

    # Now remove the entry from report_partition_info so the crontabber job
    # doesn't try to create a new partition
    op.execute("""
        DELETE FROM report_partition_info WHERE table_name = 'raw_crashes'
    """)


def downgrade():
    pass

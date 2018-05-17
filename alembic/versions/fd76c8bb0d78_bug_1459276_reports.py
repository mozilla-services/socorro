"""bug 1459276 reports

Revision ID: fd76c8bb0d78
Revises: 95c0d0f618dc
Create Date: 2018-05-11 20:28:13.465940

"""

from alembic import op

from socorro.lib.migrations import load_stored_proc


# revision identifiers, used by Alembic.
revision = 'fd76c8bb0d78'
down_revision = '95c0d0f618dc'


def upgrade():
    # Update backfill_matviews removing the reports bits
    load_stored_proc(op, ['backfill_matviews.sql'])

    op.execute(
        'DROP FUNCTION IF EXISTS reports_clean_weekly_partition(timestamp with time zone, text)'
    )
    op.execute(
        'DROP FUNCTION IF EXISTS '
        'backfill_reports_clean(timestamp with time zone, timestamp with time zone)'
    )
    op.execute('DROP FUNCTION IF EXISTS reports_clean_done(date, interval)')
    op.execute(
        'DROP FUNCTION IF EXISTS '
        'update_reports_duplicates(timestamp with time zone, timestamp with time zone)'
    )
    op.execute('DROP FUNCTION IF EXISTS update_os_versions(date)')
    op.execute('DROP FUNCTION IF EXISTS update_lookup_new_reports(text)')
    op.execute('DROP FUNCTION IF EXISTS update_os_versions_new_reports()')
    op.execute(
        'DROP FUNCTION IF EXISTS '
        'update_reports_clean(timestamp with time zone, interval, boolean, boolean)'
    )

    op.execute('DROP TABLE IF EXISTS reports_bad')
    op.execute('DROP TABLE IF EXISTS reports_duplicates')
    op.execute('DROP TABLE IF EXISTS reports_user_info')

    # Get rid of all tables that start with 'reports_clean'
    connection = op.get_bind()
    cursor = connection.connection.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name like 'reports_clean%'
    """)
    all_table_names = []
    for records in cursor.fetchall():
        all_table_names.append(records[0])

    # Sort table names so 'reports_clean' is last since the others depend on it and
    # delete them in that order
    all_table_names.sort(reverse=True)
    for table_name in all_table_names:
        op.execute('DROP TABLE IF EXISTS {}'.format(table_name))

    # Now remove the entry from report_partition_info so the crontabber job
    # doesn't try to create a new partition
    op.execute("""
        DELETE FROM report_partition_info WHERE table_name = 'reports_clean'
    """)

    # Get rid of all tables that start with 'reports'
    connection = op.get_bind()
    cursor = connection.connection.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name like 'reports%'
    """)
    all_table_names = []
    for records in cursor.fetchall():
        all_table_names.append(records[0])

    # Sort table names so 'reports' is last since the others depend on it and
    # delete them in that order
    all_table_names.sort(reverse=True)
    for table_name in all_table_names:
        op.execute('DROP TABLE IF EXISTS {}'.format(table_name))

    # Now remove the entry from report_partition_info so the crontabber job
    # doesn't try to create a new partition
    op.execute("""
        DELETE FROM report_partition_info WHERE table_name = 'reports'
    """)


def downgrade():
    pass

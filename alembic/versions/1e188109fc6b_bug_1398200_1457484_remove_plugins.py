"""bug 1398200, 1457484 remove unused tables

Revision ID: 1e188109fc6b
Revises: 8e8390138426
Create Date: 2018-04-27 14:12:16.709146

"""

from alembic import op

from socorro.lib.migrations import load_stored_proc


# revision identifiers, used by Alembic.
revision = '1e188109fc6b'
down_revision = '8e8390138426'


def upgrade():
    op.execute('DROP TABLE IF EXISTS plugins')
    op.execute('DROP TABLE IF EXISTS release_channel_matches')
    op.execute('DROP TABLE IF EXISTS replication_test')
    op.execute('DROP TABLE IF EXISTS sessions')
    op.execute('DROP TABLE IF EXISTS socorro_db_version')
    op.execute('DROP TABLE IF EXISTS socorro_db_version_history')
    op.execute('DROP TABLE IF EXISTS transform_rules')
    op.execute('DROP TABLE IF EXISTS crashes_by_user')
    op.execute('DROP TABLE IF EXISTS crashes_by_user_build')
    op.execute('DROP TABLE IF EXISTS uptime_levels')
    op.execute('DROP TABLE IF EXISTS modules')
    op.execute('DROP TABLE IF EXISTS crash_types')
    op.execute('DROP TABLE IF EXISTS process_types')
    op.execute('DROP TABLE IF EXISTS rank_compare')

    op.execute('DROP FUNCTION IF EXISTS backfill_rank_compare(date)')
    op.execute('DROP FUNCTION IF EXISTS update_rank_compare(date, boolean, interval)')

    # Load the new version of backfill_matviews
    load_stored_proc(op, ['backfill_matviews.sql'])


def downgrade():
    # There is no going back
    pass

"""remove last remaining stored procedures and tables from crash saving

Revision ID: 0db05da17ae8
Revises: bddacdadc175
Create Date: 2018-05-15 12:36:28.589422

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '0db05da17ae8'
down_revision = 'bddacdadc175'


def upgrade():
    op.execute('DROP FUNCTION IF EXISTS crash_hadu(bigint, bigint, numeric)')
    op.execute('DROP FUNCTION IF EXISTS crash_hadu(bigint, numeric, numeric)')
    op.execute('DROP FUNCTION IF EXISTS create_os_version_string(citext, integer, integer)')
    op.execute(
        'DROP FUNCTION IF EXISTS '
        'create_weekly_partition(citext, date, text, text, text[], text[], text[], boolean, text)'
    )
    op.execute('DROP FUNCTION IF EXISTS get_cores(text)')
    op.execute(
        'DROP FUNCTION IF EXISTS '
        'same_time_fuzzy(timestamp with time zone, timestamp with time zone, integer, integer)'
    )
    op.execute('DROP FUNCTION IF EXISTS try_lock_table(text, text, integer)')
    op.execute('DROP FUNCTION IF EXISTS url2domain(text)')
    op.execute(
        'DROP FUNCTION IF EXISTS utc_day_is(timestamp with time zone, timestamp without time zone)'
    )
    op.execute('DROP FUNCTION IF EXISTS week_begins_partition_string(text)')
    op.execute('DROP FUNCTION IF EXISTS week_begins_partition(text)')
    op.execute('DROP FUNCTION IF EXISTS week_begins_utc(timestamp with time zone)')
    op.execute('DROP FUNCTION IF EXISTS week_ends_partition_string(text)')
    op.execute('DROP FUNCTION IF EXISTS week_ends_partition(text)')

    op.execute('DROP TABLE IF EXISTS windows_versions')
    op.execute('DROP TABLE IF EXISTS reasons')
    op.execute('DROP TABLE IF EXISTS os_versions')
    op.execute('DROP TABLE IF EXISTS domains')
    op.execute('DROP TABLE IF EXISTS addresses')
    op.execute('DROP TABLE IF EXISTS flash_versions')


def downgrade():
    pass

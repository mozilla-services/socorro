"""bug 1440471 remove raw_update_channels

Revision ID: 3474e98b321f
Revises: 1e188109fc6b
Create Date: 2018-04-28 15:27:18.356710

"""

from alembic import op

from socorro.lib.migrations import load_stored_proc


# revision identifiers, used by Alembic.
revision = '3474e98b321f'
down_revision = '1e188109fc6b'


def upgrade():
    # Update changed stored procedures
    load_stored_proc(op, ['backfill_matviews.sql'])
    load_stored_proc(op, ['update_product_versions.sql'])

    # Bug 1440471
    op.execute('DROP TABLE IF EXISTS raw_update_channels')
    op.execute('DROP TABLE IF EXISTS update_channel_map')

    op.execute(
        'DROP FUNCTION IF EXISTS '
        'update_raw_update_channel(timestamp, interval, boolean, boolean, text)'
    )
    op.execute('DROP FUNCTION IF EXISTS backfill_raw_update_channel(timestamp, timestamp)')


def downgrade():
    # There is no going back
    pass

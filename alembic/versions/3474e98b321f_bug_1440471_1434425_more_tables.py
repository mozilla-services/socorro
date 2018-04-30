"""bug 1440471, 1434425 remove raw_update_channels and graphics_device things

This doesn't remove the graphics_device table--we're passing that to
Django-land. This does remove the stored procedures that manipulate it.

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

    # Bug 1434425
    op.execute('DROP FUNCTION IF EXISTS backfill_graphics_devices(date)')
    op.execute('DROP FUNCTION IF EXISTS update_graphics_devices(date, boolean)')


def downgrade():
    # There is no going back
    pass

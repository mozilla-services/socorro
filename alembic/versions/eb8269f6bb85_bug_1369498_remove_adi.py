"""bug 1369498 remove adi

Remove ADI-related tables and stored procedures.

Revision ID: eb8269f6bb85
Revises: 0db05da17ae8
Create Date: 2018-07-19 20:00:52.933551

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'eb8269f6bb85'
down_revision = '0db05da17ae8'


def upgrade():
    # Remove tables
    for table in ('raw_adi_logs',
                  'raw_adi',
                  'build_adu',
                  'product_adu'):
        op.execute('DROP TABLE IF EXISTS %s' % table)

    # Remove stored procedures
    for proc in ('backfill_adu(date)',
                 'backfill_build_adu(date)',
                 'backfill_matviews(date, date, boolean, interval)',
                 'update_adu(date, boolean)',
                 'update_build_adu(date, boolean)'):
        op.execute('DROP FUNCTION IF EXISTS %s' % proc)


def downgrade():
    # No going back
    pass

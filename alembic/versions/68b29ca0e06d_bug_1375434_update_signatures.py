"""bug 1375434 update signatures

Revision ID: 68b29ca0e06d
Revises: e70541df7ed7
Create Date: 2018-05-04 14:43:21.330446

"""

from alembic import op
from socorro.lib.migrations import load_stored_proc


# revision identifiers, used by Alembic.
revision = '68b29ca0e06d'
down_revision = 'e70541df7ed7'


def upgrade():
    # Delete the stored procedures
    op.execute('DROP FUNCTION IF EXISTS update_signatures(date, boolean)')
    op.execute('DROP FUNCTION IF EXISTS update_signatures_hourly(timestamp, interval, boolean)')

    # Load the new version of backfill_matviews
    load_stored_proc(op, ['backfill_matviews.sql'])


def downgrade():
    # No going back
    pass

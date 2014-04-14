"""bug 967593 - GC crash count

Revision ID: 6ef54091228
Revises: 22ec34ad88fc
Create Date: 2014-02-04 11:01:07.716720

"""

# revision identifiers, used by Alembic.
revision = '6ef54091228'
down_revision = '22ec34ad88fc'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['update_gccrashes.sql', 'backfill_gccrashes.sql',
                          'backfill_matviews.sql'])
    op.create_table(u'gccrashes',
        sa.Column(u'report_date', postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(u'product_version_id', postgresql.INTEGER(), nullable=False),
        sa.Column(u'build', sa.NUMERIC(), nullable=True),
        sa.Column(u'is_gc_count', sa.INTEGER(), nullable=False)
    )
    fix_permissions(op, 'gccrashes')


def downgrade():
    load_stored_proc(op, ['backfill_matviews.sql'])
    op.execute("""
        DROP FUNCTION update_gccrashes(date, boolean, interval)
    """)
    op.execute("""
        DROP FUNCTION backfill_gccrashes(date, boolean, interval)
    """)
    op.drop_table(u'gccrashes')

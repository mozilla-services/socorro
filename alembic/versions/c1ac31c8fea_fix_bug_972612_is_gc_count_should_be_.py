"""fix bug 972612 - is_gc_count should be per-ADU

Revision ID: c1ac31c8fea
Revises: 1aa9adb91413
Create Date: 2014-02-13 15:14:23.916163

"""

# revision identifiers, used by Alembic.
revision = 'c1ac31c8fea'
down_revision = '491cdcf9f97c'

import datetime

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['crash_madu.sql', 'update_gccrashes.sql'])
    op.execute(""" TRUNCATE gccrashes """)
    op.alter_column(u'gccrashes', u'is_gc_count',
                    new_column_name=u'gc_count_madu', type_=sa.REAL())
    now = datetime.datetime.utcnow()
    for backfill_date in [
        (now - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            for days in range(1,30)]:
                op.execute(""" SELECT backfill_gccrashes('%s') """ % backfill_date)
                op.execute(""" COMMIT """)



def downgrade():
    load_stored_proc(op, ['update_gccrashes.sql'])
    op.execute(""" DROP FUNCTION crash_madu(bigint, numeric, numeric) """)
    op.alter_column(u'gccrashes', u'gc_count_madu',
                    new_column_name=u'is_gc_count', type_=sa.INT())

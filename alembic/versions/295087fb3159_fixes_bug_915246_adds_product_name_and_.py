"""Fixes bug 915246 adds product_name and updates crash_adu_by_build_signature procs

Revision ID: 295087fb3159
Revises: 21887d27b1c4
Create Date: 2014-04-29 13:34:35.178817

"""
import datetime

# revision identifiers, used by Alembic.
revision = '295087fb3159'
down_revision = '21887d27b1c4'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute("""
        TRUNCATE crash_adu_by_build_signature
    """)
    op.add_column(u'crash_adu_by_build_signature',
        sa.Column(u'product_name', sa.TEXT(), nullable=False)
    )

    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql',
                          'backfill_crash_adu_by_build_signature.sql'])

    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    for i in range(0,7):
        op.execute("""
            SELECT backfill_crash_adu_by_build_signature(
                ('%s'::date - '%s days'::interval)::date
            )
        """  % (today, i))

def downgrade():
    ## Note that we truncated the data, so we aren't going to restore it
    ## The data in this report was incorrect/bad anyway
    op.drop_column(u'crash_adu_by_build_signature', u'product_name')
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql',
                          'backfill_crash_adu_by_build_signature.sql'])


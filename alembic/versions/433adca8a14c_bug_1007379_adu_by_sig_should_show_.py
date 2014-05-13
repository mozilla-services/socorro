"""bug 1007379 adu-by-sig should show crashcount of 0

Revision ID: 433adca8a14c
Revises: 1495b7307dd3
Create Date: 2014-05-13 15:04:14.880767

"""

# revision identifiers, used by Alembic.
revision = '433adca8a14c'
down_revision = '1495b7307dd3'

import datetime

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql'])

    op.execute("""
        TRUNCATE crash_adu_by_build_signature
    """)

    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    for i in range(0,7):
        op.execute("""
            SELECT backfill_crash_adu_by_build_signature(
                ('%s'::date - '%s days'::interval)::date
            )
        """  % (today, i))


def downgrade():
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql'])

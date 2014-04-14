"""Backfill graphics devices signature summary

Revision ID: 317e15fbf13a
Revises: 191d0453cc07
Create Date: 2013-10-30 11:19:55.285514

"""

# revision identifiers, used by Alembic.
revision = '317e15fbf13a'
down_revision = '191d0453cc07'

from alembic import op
from socorro.lib import citexttype, jsontype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    # backfill data for a few days
    load_stored_proc(op, ['update_signature_summary_graphics.sql',
        'backfill_signature_summary_graphics.sql',
        'update_signature_summary_devices.sql',
        'backfill_signature_summary_devices.sql',
    ])

    for i in range(15, 30):
        backfill_date = '2013-10-%s' % i
        op.execute("""
            SELECT backfill_signature_summary_graphics('%s')
        """ % backfill_date)
        op.execute("""
            SELECT backfill_signature_summary_devices('%s')
        """ % backfill_date)
        op.execute(""" COMMIT """)


def downgrade():
    op.execute("""
        DROP FUNCTION update_signature_summary_graphics(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION update_signature_summary_devices(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION backfill_signature_summary_devices(date)
    """)
    op.execute("""
        DROP FUNCTION backfill_signature_summary_graphics(date)
    """)

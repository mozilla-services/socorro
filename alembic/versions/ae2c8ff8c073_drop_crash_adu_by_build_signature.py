"""drop crash_adu_by_build_signature

Revision ID: ae2c8ff8c073
Revises: 07c6633fa1b6
Create Date: 2017-09-07 19:28:29.440266

"""

from alembic import op
from socorro.lib.migrations import load_stored_proc

# revision identifiers, used by Alembic.
revision = 'ae2c8ff8c073'
down_revision = '07c6633fa1b6'


def upgrade():
    op.execute("""
        DROP TABLE IF EXISTS crash_adu_by_build_signature
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        update_crash_adu_by_build_signature(date, boolean)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS
        backfill_crash_adu_by_build_signature(date)
    """)
    load_stored_proc(op, ['backfill_matviews.sql'])


def downgrade():
    # There is no going back.
    pass

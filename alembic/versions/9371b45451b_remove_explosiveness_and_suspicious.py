"""Remove everything that has to do with explosive and suspicious crashes.

Revision ID: 9371b45451b
Revises: 2990eb43b269
Create Date: 2016-01-20 13:25:27.414375

"""

from alembic import op
from socorrolib.lib.migrations import load_stored_proc

# revision identifiers, used by Alembic.
revision = '9371b45451b'
down_revision = '2990eb43b269'


def upgrade():
    op.execute("""
        DROP TABLE suspicious_crash_signatures
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS backfill_explosiveness (date)
    """)
    op.execute("""
        DROP FUNCTION IF EXISTS update_explosiveness (date, boolean, interval)
    """)
    op.execute('COMMIT')
    load_stored_proc(op, ['backfill_matviews.sql'])


def downgrade():
    op.execute("""
        CREATE TABLE suspicious_crash_signatures (
            suspicious_crash_signature_id integer NOT NULL,
            signature_id integer,
            report_date timestamp with time zone
        )
    """)
    # This doesn't actually have to be the real function. Just something so the
    # downgrade works in alembic integration testing in Travis.
    op.execute("""
        CREATE OR REPLACE FUNCTION backfill_explosiveness(updateday date)
        RETURNS boolean
        LANGUAGE plpgsql
            AS $$
        BEGIN
        RETURN TRUE;
        END; $$;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_explosiveness(updateday date)
        RETURNS boolean
        LANGUAGE plpgsql
            AS $$
        BEGIN
        RETURN TRUE;
        END; $$;
    """)
    op.execute('COMMIT')

    load_stored_proc(op, ['backfill_matviews.sql'])

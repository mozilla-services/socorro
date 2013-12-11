"""bug 822304 priority jobs removal

Revision ID: 144f7ace11e7
Revises: 3a5471a358bf
Create Date: 2013-12-11 09:22:35.674934

"""

# revision identifiers, used by Alembic.
revision = '144f7ace11e7'
down_revision = '3a5471a358bf'

from alembic import op
from socorro.lib import citexttype, jsontype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from sqlalchemy.dialects import postgresql


def upgrade():
    op.drop_table(u'priority_jobs')

    op.execute("""
        DO $$
            DECLARE prjobs_tablename text;
        BEGIN
            FOR prjobs_tablename IN select relname::text from pg_class WHERE relname ~ 'priority_jobs_' and relkind = 'r'
        LOOP
            EXECUTE format('DROP TABLE %s', prjobs_tablename);
        END LOOP;

        END$$
    """)

def downgrade():
    op.create_table(u'priority_jobs',
        sa.Column(u'uuid', sa.TEXT(), nullable=False)
    )
    # Don't restore per-processor priority_jobs tables
    # (processors create them on their own)

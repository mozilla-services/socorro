"""Fixes bug 1136854 fix permissions issues, cleanup procs

Revision ID: 63d05b930c3
Revises: 4f071c465f0e
Create Date: 2015-02-25 11:37:18.627333

"""

# revision identifiers, used by Alembic.
revision = '63d05b930c3'
down_revision = '732abe64c5a'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, [
        'create_weekly_partition.sql',
        'nonzero_string.sql',
        'reports_clean_weekly_partition.sql',
    ])

    op.execute('DROP FUNCTION IF EXISTS pg_stat_statements()')
    op.execute('DROP FUNCTION IF EXISTS pg_stat_statements_reset()')


def downgrade():
    load_stored_proc(op, [
        'create_weekly_partition.sql',
        'nonzero_string.sql',
        'reports_clean_weekly_partition.sql',
        'pg_stat_statements.sql',
        'pg_stat_statements_reset.sql',
    ])

"""Reload update_reports_duplicates()

Revision ID: 42c267d6ed35
Revises: 5387d590bc45
Create Date: 2015-01-15 15:31:14.012678

"""

# revision identifiers, used by Alembic.
revision = '42c267d6ed35'
down_revision = 'e4ea2ae3413'

from alembic import op
from socorrolib.lib import citexttype, jsontype, buildtype
from socorrolib.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['update_reports_duplicates.sql'])


def downgrade():
    load_stored_proc(op, ['update_reports_duplicates.sql'])

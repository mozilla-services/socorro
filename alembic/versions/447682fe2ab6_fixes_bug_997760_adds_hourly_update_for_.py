"""Fixes bug 997760 adds hourly update for signatures

Revision ID: 447682fe2ab6
Revises: 80de14da49b
Create Date: 2014-04-17 09:22:09.627456

"""

# revision identifiers, used by Alembic.
revision = '447682fe2ab6'
down_revision = '80de14da49b'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_signatures.sql', 'update_signatures_hourly.sql'])

def downgrade():
    load_stored_proc(op, ['update_signatures.sql'])
    op.execute("DROP FUNCTION update_signatures_hourly(timestamptz, interval, boolean)")

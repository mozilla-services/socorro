"""Nobug - load update_reports_clean from contributor fix

Revision ID: 1ef041dfc3d5
Revises: 1ab8d5514ce2
Create Date: 2014-06-12 12:56:37.525463

"""

# revision identifiers, used by Alembic.
revision = '1ef041dfc3d5'
down_revision = '1ab8d5514ce2'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    load_stored_proc(op, ['001_update_reports_clean.sql'])

def downgrade():
    load_stored_proc(op, ['001_update_reports_clean.sql'])

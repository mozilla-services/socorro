"""Fixes bug 1023867 fixes integer overflow in fuzzy date math function

Revision ID: 1ab8d5514ce2
Revises: 433adca8a14c
Create Date: 2014-06-11 10:24:03.492330

"""

# revision identifiers, used by Alembic.
revision = '1ab8d5514ce2'
down_revision = '433adca8a14c'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    load_stored_proc(op, ['same_time_fuzzy.sql'])

def downgrade():
    load_stored_proc(op, ['same_time_fuzzy.sql'])

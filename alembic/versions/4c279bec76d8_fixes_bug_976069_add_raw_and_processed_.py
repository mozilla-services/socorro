"""Fixes bug 976069 add raw and processed crash to expiry

Revision ID: 4c279bec76d8
Revises: 4b2567293aee
Create Date: 2014-03-18 16:49:42.675693

"""

# revision identifiers, used by Alembic.
revision = '4c279bec76d8'
down_revision = '4b2567293aee'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['drop_old_partitions.sql', 'drop_named_partitions.sql'])

def downgrade():
    load_stored_proc(op, ['drop_old_partitions.sql'])
    op.execute(""" DROP FUNCTION drop_named_partitions(date) """)

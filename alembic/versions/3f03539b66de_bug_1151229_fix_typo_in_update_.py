"""bug 1151229 - fix typo in update_signature_summary_graphics

Revision ID: 3f03539b66de
Revises: 3e9fd64194df
Create Date: 2015-04-04 10:07:43.635536

"""

# revision identifiers, used by Alembic.
revision = '3f03539b66de'
down_revision = '3e9fd64194df'

from alembic import op
from socorrolib.lib import citexttype, jsontype, buildtype
from socorrolib.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_signature_summary_graphics.sql'])

def downgrade():
    load_stored_proc(op, ['update_signature_summary_graphics.sql'])

"""empty message

Revision ID: 1961d1f70175
Revises: 295087fb3159
Create Date: 2014-05-02 16:15:05.251992

"""

# revision identifiers, used by Alembic.
revision = '1961d1f70175'
down_revision = '295087fb3159'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['update_correlations_addon.sql',
                          'update_correlations_core.sql',
                          'update_correlations_module.sql'])


def downgrade():
    load_stored_proc(op, ['update_correlations_addon.sql',
                          'update_correlations_core.sql',
                          'update_correlations_module.sql'])

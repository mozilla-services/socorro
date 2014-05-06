"""bug 1005326 - filter out NULL

Revision ID: 1495b7307dd3
Revises: cef861648c
Create Date: 2014-05-06 16:40:36.199526

"""

# revision identifiers, used by Alembic.
revision = '1495b7307dd3'
down_revision = 'cef861648c'

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

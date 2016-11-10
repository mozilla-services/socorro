"""bug 1030218 - group correlations by reason

Revision ID: 26521f842be2
Revises: 3e872b0759f0
Create Date: 2014-06-25 11:53:34.946160

"""

# revision identifiers, used by Alembic.
revision = '26521f842be2'
down_revision = '3e872b0759f0'

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
    op.execute(""" TRUNCATE correlations_addon, correlations_core, correlations_module""")
    op.add_column(u'correlations_addon', sa.Column('reason_id', sa.INTEGER(), nullable=False))
    op.add_column(u'correlations_core', sa.Column('reason_id', sa.INTEGER(), nullable=False))
    op.add_column(u'correlations_module', sa.Column('reason_id', sa.INTEGER(), nullable=False))

def downgrade():
    load_stored_proc(op, ['update_correlations_addon.sql',
                          'update_correlations_core.sql',
                          'update_correlations_module.sql'])
    op.drop_column(u'correlations_module', 'reason_id')
    op.drop_column(u'correlations_core', 'reason_id')
    op.drop_column(u'correlations_addon', 'reason_id')

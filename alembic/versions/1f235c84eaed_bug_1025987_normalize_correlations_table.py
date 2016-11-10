"""bug 1025987 - normalize correlations table

Revision ID: 1f235c84eaed
Revises: 3f007539efc
Create Date: 2014-06-16 11:39:27.307789

"""

# revision identifiers, used by Alembic.
revision = '1f235c84eaed'
down_revision = '3f007539efc'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_correlations_module.sql'])
    op.execute(""" TRUNCATE correlations_module """)
    op.create_table('modules',
    sa.Column('module_id', sa.INTEGER(), nullable=False),
    sa.Column('name', sa.TEXT(), nullable=False),
    sa.Column('version', sa.TEXT(), nullable=False),
    sa.PrimaryKeyConstraint('module_id', 'name', 'version')
    )
    op.add_column(u'correlations_module', sa.Column('module_id', sa.INTEGER(), nullable=False))
    op.drop_column(u'correlations_module', 'module_name')
    op.drop_column(u'correlations_module', 'module_version')


def downgrade():
    load_stored_proc(op, ['update_correlations_module.sql'])
    op.add_column(u'correlations_module', sa.Column('module_version', sa.TEXT(), nullable=False))
    op.add_column(u'correlations_module', sa.Column('module_name', sa.TEXT(), nullable=False))
    op.drop_column(u'correlations_module', 'module_id')
    op.drop_table('modules')

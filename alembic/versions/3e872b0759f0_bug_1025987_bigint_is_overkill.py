"""bug 1025987 - BIGINT is overkill

Revision ID: 3e872b0759f0
Revises: 1f235c84eaed
Create Date: 2014-06-17 09:52:29.095452

"""

# revision identifiers, used by Alembic.
revision = '3e872b0759f0'
down_revision = '1f235c84eaed'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.alter_column(u'correlations_addon', u'total',
               type_=sa.INTEGER(),
               nullable=False)
    op.alter_column(u'correlations_core', u'total',
               type_=sa.INTEGER(),
               nullable=False)
    op.alter_column(u'correlations_module', u'total',
               type_=sa.INTEGER(),
               nullable=False)

def downgrade():
    op.alter_column(u'correlations_addon', u'total',
               type_=sa.BIGINT(),
               nullable=False)
    op.alter_column(u'correlations_core', u'total',
               type_=sa.BIGINT(),
               nullable=False)
    op.alter_column(u'correlations_module', u'total',
               type_=sa.BIGINT(),
               nullable=False)

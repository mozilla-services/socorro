"""Add lag_log table

Revision ID: 355d0795af7f
Revises: 4f87c13b66c5
Create Date: 2014-01-21 14:49:57.297244

"""

# revision identifiers, used by Alembic.
revision = '355d0795af7f'
down_revision = '4f87c13b66c5'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(u'lag_log',
        sa.Column(u'replica_name', sa.TEXT(), nullable=False),
        sa.Column(u'moment', postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(u'lag', sa.INTEGER(), nullable=False),
        sa.Column(u'master', sa.TEXT(), nullable=False)
    )


def downgrade():
    op.drop_table(u'lag_log')

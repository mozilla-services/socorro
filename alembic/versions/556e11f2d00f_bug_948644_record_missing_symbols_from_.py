"""bug 948644 - record missing symbols from the processor

Revision ID: 556e11f2d00f
Revises: 17e83fdeb135
Create Date: 2014-11-18 12:50:20.496750

"""

# revision identifiers, used by Alembic.
revision = '556e11f2d00f'
down_revision = '17e83fdeb135'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.create_table('missing_symbols',
    sa.Column('date_processed', sa.DATE(), nullable=False),
    sa.Column('debug_file', sa.TEXT(), nullable=True),
    sa.Column('debug_id', sa.TEXT(), nullable=True),

def downgrade():
    op.drop_table('alembic_version')
    op.drop_table('missing_symbols')

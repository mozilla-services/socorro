"""bug 948644 - add filename and version to missing_symbols

Revision ID: 5674c7b2ff01
Revises: 556e11f2d00f
Create Date: 2014-11-26 11:56:44.278539

"""

# revision identifiers, used by Alembic.
revision = '5674c7b2ff01'
down_revision = '556e11f2d00f'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.add_column(u'missing_symbols',
            sa.Column('filename', sa.TEXT(), nullable=True)
    )
    op.add_column(u'missing_symbols',
            sa.Column('version', sa.TEXT(), nullable=True)
    )

def downgrade():
    op.drop_column(u'missing_symbols', 'version')
    op.drop_column(u'missing_symbols', 'filename')

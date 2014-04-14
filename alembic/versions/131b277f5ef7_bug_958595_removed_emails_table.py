"""Bug 958595 - Removed emails table.

Revision ID: 131b277f5ef7
Revises: 6ef54091228
Create Date: 2014-02-10 17:05:16.106061

"""

# revision identifiers, used by Alembic.
revision = '131b277f5ef7'
down_revision = '6ef54091228'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


class CITEXT(types.UserDefinedType):
    name = 'citext'

    def get_col_spec(self):
        return 'CITEXT'

    def bind_processor(self, dialect):
        return lambda value: value

    def result_processor(self, dialect, coltype):
        return lambda value: value

    def __repr__(self):
        return "citext"


def upgrade():
    op.drop_table(u'emails')


def downgrade():
    op.create_table(
        u'emails',
        sa.Column(u'email', CITEXT(), nullable=False, primary_key=True),
        sa.Column(u'last_sending', sa.TIMESTAMP(timezone=True)),
    )

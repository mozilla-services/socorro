"""Adding in a suspicious crash table

Revision ID: 2c03d8ea0a50
Revises: 35604f61bc24
Create Date: 2013-08-09 18:46:42.618063

"""

# revision identifiers, used by Alembic.
revision = '2c03d8ea0a50'
down_revision = '35604f61bc24'

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
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

class JSON(types.UserDefinedType):
    name = 'json'

    def get_col_spec(self):
        return 'JSON'

    def bind_processor(self, dialect):
        return lambda value: value

    def result_processor(self, dialect, coltype):
        return lambda value: value

    def __repr__(self):
        return "json"

def upgrade():
    op.create_table(u'suspicious_crash_signatures',
        sa.Column(u'suspicious_crash_signature_id', sa.INTEGER()),
        sa.Column(u'signature_id', sa.INTEGER()),
        sa.Column(u'report_date', sa.TIMESTAMP(timezone=True))
    )


def downgrade():
    op.drop_table(u'suspicious_crash_signatures')

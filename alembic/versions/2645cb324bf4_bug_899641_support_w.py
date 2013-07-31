"""bug 899641 Support Windows NT 6.3

Revision ID: 2645cb324bf4
Revises: 11cd71153550
Create Date: 2013-07-30 13:09:47.577306

"""

# revision identifiers, used by Alembic.
revision = '2645cb324bf4'
down_revision = '11cd71153550'

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
    op.execute("""
        INSERT INTO windows_versions
        (windows_version_name, major_version, minor_version)
        VALUES('Windows 8.1', 6, 3)
    """)

def downgrade():
    op.execute("""
        DELETE FROM windows_versions
        WHERE windows_version_name = 'Windows 8.1'
        AND major_version = 6
        AND  minor_version = 3
    """)

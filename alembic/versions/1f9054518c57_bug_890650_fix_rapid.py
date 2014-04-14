"""bug 890650 fix rapid beta in crashes by user build

Revision ID: 1f9054518c57
Revises: 2c03d8ea0a50
Create Date: 2013-08-28 12:22:03.217984

"""

# revision identifiers, used by Alembic.
revision = '1f9054518c57'
down_revision = '2c03d8ea0a50'

import os
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
    app_path=os.getcwd()
    procs = [
        'update_build_adu.sql'
        , 'update_crashes_by_user_build.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        with open(myfile, 'r') as file:
            op.execute(file.read())


def downgrade():
    pass

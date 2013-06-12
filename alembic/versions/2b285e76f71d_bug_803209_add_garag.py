"""bug 803209 -- add garbage collection count to TCBS

Revision ID: 2b285e76f71d
Revises: 8894c185715
Create Date: 2013-06-11 12:46:09.637058

"""

# revision identifiers, used by Alembic.
revision = '2b285e76f71d'
down_revision = '8894c185715'

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

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
    op.add_column(u'tcbs', sa.Column(u'is_gc_count', sa.INTEGER(), server_default='0', nullable=False))
    op.add_column(u'tcbs_build', sa.Column(u'is_gc_count', sa.INTEGER(), server_default='0', nullable=False))
    app_path=os.getcwd()
    procs = [
        'backfill_matviews.sql',
        'update_tcbs.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        with open(myfile, 'r') as file:
            op.execute(file.read())

def downgrade():
    op.drop_column(u'tcbs_build', u'is_gc_count')
    op.drop_column(u'tcbs', u'is_gc_count')

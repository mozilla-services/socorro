"""bug905346-fix-timezone-constraints

Revision ID: 4de11772649b
Revises: 35604f61bc24
Create Date: 2013-08-16 10:17:37.874415

"""

# revision identifiers, used by Alembic.
revision = '4de11772649b'
down_revision = '1f9054518c57'

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
    op.add_column(u'report_partition_info', sa.Column(u'timetype', sa.TEXT()))
    op.execute("""
        UPDATE report_partition_info SET timetype = 'TIMESTAMPTZ'
            where partition_column = 'date_processed'
    """)
    op.execute("""
        UPDATE report_partition_info SET timetype = 'DATE'
            where partition_column = 'report_date'
    """)
    op.alter_column(u'report_partition_info', u'timetype', nullable=False)

    op.execute("""
        DROP FUNCTION IF EXISTS create_weekly_partition(citext, date, text, text, text[], text[], text[], boolean)
    """)

    app_path=os.getcwd()
    procs = [
              'create_weekly_partition.sql'
            , 'weekly_report_partitions.sql'
            ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        proc = open(myfile, 'r').read()
        op.execute(proc)

def downgrade():
    op.drop_column(u'report_partition_info', u'timetype')

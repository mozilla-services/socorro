"""bug 826564 - add exploitability to reports_clean

Revision ID: 9798b1cc04
Revises: 3805e9f77df4
Create Date: 2013-06-05 13:20:25.116074

"""

# revision identifiers, used by Alembic.
revision = '9798b1cc04'
down_revision = '3805e9f77df4'

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
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return "citext"

class JSON(types.UserDefinedType):
    name = 'json'

    def get_col_spec(self):
        return 'JSON'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return "json"

def upgrade():
    op.create_table(u'exploitability_reports',
    sa.Column(u'signature_id', sa.INTEGER(), nullable=False),
    sa.Column(u'report_date', sa.DATE(), nullable=False),
    sa.Column(u'null_count', sa.INTEGER(), server_default='0', nullable=False),
    sa.Column(u'none_count', sa.INTEGER(), server_default='0', nullable=False),
    sa.Column(u'low_count', sa.INTEGER(), server_default='0', nullable=False),
    sa.Column(u'medium_count', sa.INTEGER(), server_default='0', nullable=False),
    sa.Column(u'high_count', sa.INTEGER(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['signature_id'], [u'signatures.signature_id'], ),
    sa.PrimaryKeyConstraint()
    )
    # We can probably get away with just applying this to the parent table
    # If there are performance problems on stage, break this out and apply to all
    # child partitions first, then reports_clean last.
    op.add_column(u'reports_clean', sa.Column(u'exploitability', sa.TEXT(), nullable=True))
    app_path=os.getcwd()
    procs = [
        '001_update_reports_clean.sql'
        , 'update_exploitability.sql'
        , 'backfill_exploitability.sql'
     ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        proc = open(myfile, 'r').read()
        op.execute(proc)

def downgrade():
    op.drop_column(u'reports_clean', u'exploitability')
    op.drop_table(u'exploitability_reports')
    # Not rolling back 001_update_reports_clean.sql...
    # if rolling back, need to pull out the old version and apply manually

"""bug 875352 Add weekly partition backfill function

Revision ID: 3805e9f77df4
Revises: 4d86b4efd25d
Create Date: 2013-05-23 12:05:42.774042

"""

# revision identifiers, used by Alembic.
revision = '3805e9f77df4'
down_revision = '4d86b4efd25d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column

import os

def upgrade():

    app_path=os.getcwd()
    procs = [ 'backfill_weekly_report_partitions.sql' ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        proc = open(myfile, 'r').read()
        op.execute(proc)
    # Now run this against the raw_crashes table
    op.execute("""
        SELECT backfill_weekly_report_partitions('2012-01-02',
            '2013-03-04', 'raw_crashes')
    """)

def downgrade():
    # Tricky. Need to checkout previous revision in repo
    # to do this, so leaving for now.
    return True

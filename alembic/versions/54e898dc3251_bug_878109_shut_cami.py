"""bug 878109 shut camino down

Revision ID: 54e898dc3251
Revises: 471c6efadde
Create Date: 2013-07-03 09:21:07.627571

"""

# revision identifiers, used by Alembic.
revision = '54e898dc3251'
down_revision = '471c6efadde'

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column


def upgrade():
    app_path=os.getcwd()
    procs = [ '001_update_reports_clean.sql' ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        proc = open(myfile, 'r').read()
        op.execute(proc)

def downgrade():
    ### Nothing to do here
    pass

"""bug 889151 add exploitability_report to backfill_matviews

Revision ID: 3e70bfd1ab0c
Revises: 2cbb29fc9b77
Create Date: 2013-07-01 16:57:54.489943

"""

# revision identifiers, used by Alembic.
revision = '3e70bfd1ab0c'
down_revision = '2cbb29fc9b77'

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column

def upgrade():
    app_path=os.getcwd()
    procs = [
        'backfill_matviews.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        with open(myfile, 'r') as file:
            op.execute(file.read())

def downgrade():
    pass

"""bug 886917 Add is_gc_count to tcbs_build report

Revision ID: 4d4b48f86d4b
Revises: 2b285e76f71d
Create Date: 2013-06-25 11:29:22.679634

"""

# revision identifiers, used by Alembic.
revision = '4d4b48f86d4b'
down_revision = '2b285e76f71d'

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column

def upgrade():
    app_path=os.getcwd()
    procs = [
        'update_tcbs_build.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        with open(myfile, 'r') as file:
            op.execute(file.read())

def downgrade():
    pass

"""bug 880378 make update_adu throw exceptions

Revision ID: 2cbb29fc9b77
Revises: 2b285e76f71d
Create Date: 2013-06-28 15:09:38.750774

"""

# revision identifiers, used by Alembic.
revision = '2cbb29fc9b77'
down_revision = '4d4b48f86d4b'

import os
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column

def upgrade():
    app_path=os.getcwd()
    procs = [
        'update_adu.sql'
        , 'update_build_adu.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        with open(myfile, 'r') as file:
            op.execute(file.read())

def downgrade():
    # No automated backout
    pass

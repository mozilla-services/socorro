"""Fix bug 1124750 - drop edit_product_info

Revision ID: 5a1b1cb955e9
Revises: e4ea2ae3413
Create Date: 2015-01-22 09:28:58.280815

"""

# revision identifiers, used by Alembic.
revision = '5a1b1cb955e9'
down_revision = 'e4ea2ae3413'

from alembic import op
from socorrolib.lib import citexttype, jsontype, buildtype
from socorrolib.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    op.execute("""
        DROP function IF EXISTS edit_product_info(
            integer,
            citext,
            text,
            text,
            date,
            date,
            boolean,
            numeric,
            text)
    """)


def downgrade():
    load_stored_proc(op, ['edit_product_info.sql'])

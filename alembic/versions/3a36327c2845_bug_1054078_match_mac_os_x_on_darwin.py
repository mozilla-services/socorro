"""bug 1054078 - match Mac OS X on Darwin

Revision ID: 3a36327c2845
Revises: 3e64019254d1
Create Date: 2014-08-14 15:50:10.518626

"""

# revision identifiers, used by Alembic.
revision = '3a36327c2845'
down_revision = '3e64019254d1'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute("""
        INSERT INTO os_name_matches
        (os_name, match_string)
        VALUES ('Mac OS X', 'Darwin%')""")

def downgrade():
    op.execute("""
        DELETE FROM os_name_matches
        WHERE os_name = 'Mac OS X'
        AND match_string = 'Darwin%'""")

"""fix invalid RAISE NOTICE in update_signatures_hourly.

Revision ID: 495bf3fcdb63
Revises: 3f007539efc
Create Date: 2014-07-07 20:33:34.634141

"""

# revision identifiers, used by Alembic.
revision = '495bf3fcdb63'
down_revision = '1baef149e5d1'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['update_signatures_hourly.sql'])


def downgrade():
    load_stored_proc(op, ['update_signatures_hourly.sql'])

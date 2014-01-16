"""Fix for bug 960621 - compensates for possible NULLs in fields

Revision ID: 4f87c13b66c5
Revises: 58ed3acc86cb
Create Date: 2014-01-16 15:09:46.543083

"""

# revision identifiers, used by Alembic.
revision = '4f87c13b66c5'
down_revision = '58ed3acc86cb'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_tcbs_build.sql', 'update_tcbs.sql'])


def downgrade():
    load_stored_proc(op, ['update_tcbs_build.sql', 'update_tcbs.sql'])

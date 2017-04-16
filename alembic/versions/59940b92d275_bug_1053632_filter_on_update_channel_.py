"""bug 1053632 - filter on update_channel ILIKE release%

Revision ID: 59940b92d275
Revises: 3294c1805e91
Create Date: 2014-08-13 22:02:08.036780

"""

# revision identifiers, used by Alembic.
revision = '59940b92d275'
down_revision = '3294c1805e91'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_adu.sql'])


def downgrade():
    load_stored_proc(op, ['update_adu.sql'])


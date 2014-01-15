"""Fixes bug 958640 adu updates

Revision ID: 58ed3acc86cb
Revises: 4a068f8838c6
Create Date: 2014-01-15 10:56:54.860954

"""

# revision identifiers, used by Alembic.
revision = '58ed3acc86cb'
down_revision = '4a068f8838c6'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_adu.sql', 'update_build_adu.sql'])


def downgrade():
    load_stored_proc(op, ['update_adu.sql', 'update_build_adu.sql'])

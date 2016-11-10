"""bug 958558 add_new_release() changes

Revision ID: 4cacd567770f
Revises: 48e9a4366530
Create Date: 2014-01-10 13:55:28.858647

"""

# revision identifiers, used by Alembic.
revision = '4cacd567770f'
down_revision = '48e9a4366530'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['add_new_release.sql'])


def downgrade():
    load_stored_proc(op, ['add_new_release.sql'])

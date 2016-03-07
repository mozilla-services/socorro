"""bug 993786 - update_crash_adu_by_build_signature-bad-buildids

Revision ID: 21e4e35689f6
Revises: 224f0fda6ecb
Create Date: 2014-04-08 18:46:19.755028

"""

# revision identifiers, used by Alembic.
revision = '21e4e35689f6'
down_revision = '224f0fda6ecb'

from alembic import op
from socorrolib.lib import citexttype, jsontype, buildtype
from socorrolib.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql'])

def downgrade():
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql'])

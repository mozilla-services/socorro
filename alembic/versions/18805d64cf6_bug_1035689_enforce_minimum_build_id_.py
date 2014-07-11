"""bug 1035689 - enforce minimum build ID length in update_crash_adu_by_build_signature

Revision ID: 18805d64cf6
Revises: 391e42da94dd
Create Date: 2014-07-11 15:22:21.430414

"""

# revision identifiers, used by Alembic.
revision = '18805d64cf6'
down_revision = '391e42da94dd'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql'])


def downgrade():
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql'])

"""bug 1037244 - switch to raw_adi

Revision ID: 3294c1805e91
Revises: 391e42da94dd
Create Date: 2014-07-10 17:23:22.769569

"""

# revision identifiers, used by Alembic.
revision = '3294c1805e91'
down_revision = '18805d64cf6'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['update_adu.sql', 'update_build_adu.sql',
                          'backfill_matviews.sql'])


def downgrade():
    load_stored_proc(op, ['update_adu.sql', 'update_build_adu.sql',
                          'backfill_matviews.sql'])


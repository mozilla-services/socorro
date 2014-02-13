"""Fixes bug 972563 - restrict gccrashes matview to nightly channel

Revision ID: 491cdcf9f97c
Revises: 1aa9adb91413
Create Date: 2014-02-13 13:33:45.814566

"""

# revision identifiers, used by Alembic.
revision = '491cdcf9f97c'
down_revision = '1aa9adb91413'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['update_gccrashes.sql'])


def downgrade():
    load_stored_proc(op, ['update_gccrashes.sql'])

"""Fixes bug 1117911 - load truncate_partitions() function

Revision ID: 1023855cf1ad
Revises: 5387d590bc45
Create Date: 2015-01-16 10:58:35.975923

"""

# revision identifiers, used by Alembic.
revision = '1023855cf1ad'
down_revision = '2cdb9abe6291'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['truncate_partitions.sql'])


def downgrade():
    load_stored_proc(op, ['truncate_partitions.sql'])

"""Merge parents

Revision ID: 1b595e72bb25
Revises: ('31168908ac42', '42c267d6ed35', '5a1b1cb955e9')
Create Date: 2015-02-25 08:25:42.163003

"""

# revision identifiers, used by Alembic.
revision = '1b595e72bb25'
down_revision = ('31168908ac42', '42c267d6ed35', '5a1b1cb955e9')

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    pass


def downgrade():
    pass


"""Fixes bug 998473 update add_new_product() build_type cast

Revision ID: 21887d27b1c4
Revises: 447682fe2ab6
Create Date: 2014-04-22 11:16:34.178684

"""

# revision identifiers, used by Alembic.
revision = '21887d27b1c4'
down_revision = '447682fe2ab6'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['add_new_product.sql'])


def downgrade():
    load_stored_proc(op, ['add_new_product.sql'])

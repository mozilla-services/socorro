"""bug 1018349 - add COALESCE to max(sort) when adding a new product

Revision ID: 1baef149e5d1
Revises: 26521f842be2
Create Date: 2014-06-25 15:04:37.934064

"""

# revision identifiers, used by Alembic.
revision = '1baef149e5d1'
down_revision = '26521f842be2'

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

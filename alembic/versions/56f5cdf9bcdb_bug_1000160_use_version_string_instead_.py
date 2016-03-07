"""bug 1000160 - Use version_string instead of release_version in update_reports_clean.

Revision ID: 56f5cdf9bcdb
Revises: 3f03539b66de
Create Date: 2015-04-29 15:01:50.954659

"""

# revision identifiers, used by Alembic.
revision = '56f5cdf9bcdb'
down_revision = '3f03539b66de'

from alembic import op
from socorrolib.lib import citexttype, jsontype, buildtype
from socorrolib.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    load_stored_proc(op, ['001_update_reports_clean.sql'])

def downgrade():
    load_stored_proc(op, ['001_update_reports_clean.sql'])

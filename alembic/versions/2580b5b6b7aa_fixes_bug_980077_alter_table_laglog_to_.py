"""Fixes bug 980077 alter table laglog to lag_log

Revision ID: 2580b5b6b7aa
Revises: c1ac31c8fea
Create Date: 2014-03-10 08:20:26.633240

"""

# revision identifiers, used by Alembic.
revision = '2580b5b6b7aa'
down_revision = 'c1ac31c8fea'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute(""" ALTER TABLE laglog RENAME TO lag_log """)


def downgrade():
    op.execute(""" ALTER TABLE lag_log RENAME TO laglog """)

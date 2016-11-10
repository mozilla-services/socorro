"""bug 1035957 - use literal NOW() for received_at, do not evaluate at migration time


Revision ID: 391e42da94dd
Revises: 495bf3fcdb63
Create Date: 2014-07-08 10:55:04.115932

"""

# revision identifiers, used by Alembic.
revision = '391e42da94dd'
down_revision = '495bf3fcdb63'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.alter_column(u'raw_adi', u'received_at', server_default=sa.text('NOW()')),


def downgrade():
    op.alter_column(u'raw_adi', u'received_at', server_default='2014-06-24 00:29:17.218147+00'),

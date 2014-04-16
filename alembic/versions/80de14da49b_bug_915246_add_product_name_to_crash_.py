"""bug 915246 - add product_name to crash_adu_by_build_signature

Revision ID: 80de14da49b
Revises: 21e4e35689f6
Create Date: 2014-04-15 13:12:37.885036

"""

# revision identifiers, used by Alembic.
revision = '80de14da49b'
down_revision = '21e4e35689f6'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

import datetime


def upgrade():
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql'])
    op.add_column(u'crash_adu_by_build_signature',
                  sa.Column(u'product_name', citexttype.CitextType(),
                  nullable=False))
    op.create_index('ix_crash_adu_by_build_signature_product_name',
                    'crash_adu_by_build_signature', [u'product_name'],
                    unique=False)
    today = datetime.datetime.utcnow()
    for i in range(0, 30):
        op.execute("""
            select
            backfill_crash_adu_by_build_signature(
              ('%s'::date - '%s days'::interval)::date) """ % (today, i))
        op.execute(""" COMMIT """)


def downgrade():
    load_stored_proc(op, ['update_crash_adu_by_build_signature.sql'])
    op.drop_index('ix_crash_adu_by_build_signature_product_name',
                  table_name='crash_adu_by_build_signature')
    op.drop_column(u'crash_adu_by_build_signature', u'product_name')

"""bug 1056025 and bug 1037855 - rename Fennec->FennecAndroid and WebappRuntime correctly

Revision ID: 52dbc7357409
Revises: 3a36327c2845
Create Date: 2014-08-20 10:15:41.198381

"""

# revision identifiers, used by Alembic.
revision = '52dbc7357409'
down_revision = '3a36327c2845'

import datetime

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    from socorro.cron.jobs.fetch_adi_from_hive import _RAW_ADI_QUERY
    op.execute("""TRUNCATE raw_adi""")
    now = datetime.datetime.utcnow()
    for backfill_date in [
        (now - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            for days in range(1,3)]:
                op.execute(_RAW_ADI_QUERY % ("'" + backfill_date + "'"))

def downgrade():
    op.execute("""TRUNCATE raw_adi""")

"""bug 1053632 - collapse raw_adi release channels

Revision ID: 3e64019254d1
Revises: 3294c1805e91
Create Date: 2014-08-13 22:45:29.624480

"""

# revision identifiers, used by Alembic.
revision = '3e64019254d1'
down_revision = '3294c1805e91'

import datetime

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    op.execute("""TRUNCATE raw_adi""")
    now = datetime.datetime.utcnow()
    for backfill_date in [
        (now - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            for days in range(1,3)]:
                op.execute("""
                    INSERT INTO raw_adi (
                        adi_count,
                        date,
                        product_name,
                        product_os_platform,
                        product_os_version,
                        product_version,
                        build,
                        product_guid,
                        update_channel
                    )
                    SELECT
                        sum(count),
                        report_date,
                        raw_adi_logs.product_name,
                        product_os_platform,
                        product_os_version,
                        product_version,
                        build,
                        CASE WHEN (product_guid = 'webapprt@mozilla.org')
                        THEN '{webapprt@mozilla.org}'
                        ELSE product_guid
                        END,
                        CASE WHEN (build_channel ILIKE 'release%%')
                        THEN 'release'
                        ELSE build_channel
                        END
                    FROM raw_adi_logs
                        -- FILTER with product_productid_map
                        JOIN product_productid_map ON productid = product_guid
                    WHERE
                        report_date='%s'
                    GROUP BY
                        report_date,
                        raw_adi_logs.product_name,
                        product_os_platform,
                        product_os_version,
                        product_version,
                        build,
                        product_guid,
                        build_channel
                """ % backfill_date)

def downgrade():
    op.execute("""TRUNCATE raw_adi""")

"""bug 1056025 and bug 1037855 - rename Fennec->FennecAndroid and WebappRuntime correctly

Revision ID: 52dbc7357409
Revises: 3a36327c2845
Create Date: 2014-08-20 10:15:41.198381

"""

# revision identifiers, used by Alembic.
revision = '52dbc7357409'
down_revision = '3a36327c2845'

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
                        CASE WHEN (raw_adi_logs.product_name = 'Fennec'
                            AND product_guid = '{aa3c5121-dab2-40e2-81ca-7ea25febc110}')
                        THEN 'FennecAndroid'
                        WHEN (raw_adi_logs.product_name = 'Webapp Runtime')
                        THEN 'WebappRuntime'
                        ELSE raw_adi_logs.product_name
                        END,
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
                        JOIN product_productid_map ON productid =
                            CASE WHEN (product_guid = 'webapprt@mozilla.org')
                            THEN '{webapprt@mozilla.org}'
                            ELSE product_guid
                            END
                    WHERE
                        report_date=%s
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

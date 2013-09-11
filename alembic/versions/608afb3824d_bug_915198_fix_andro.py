"""bug 915198 fix android devices

Revision ID: 608afb3824d
Revises: 389f5501023b
Create Date: 2013-09-11 08:32:01.500395

"""

# revision identifiers, used by Alembic.
revision = '608afb3824d'
down_revision = '389f5501023b'

import os
import datetime
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import types
from sqlalchemy.sql import table, column


def upgrade():
    app_path=os.getcwd()
    procs = [
        'update_android_devices.sql'
    ]
    for myfile in [app_path + '/socorro/external/postgresql/raw_sql/procs/' + line for line in procs]:
        with open(myfile, 'r') as file:
            op.execute(file.read())

    # Clean up our duplicates!
    op.execute("""
        DELETE FROM android_devices a
        USING (
        SELECT min(android_device_id) as android_device_id,
                android_cpu_abi, android_manufacturer, android_model, android_version
        FROM android_devices
                GROUP BY android_cpu_abi, android_manufacturer, android_model, android_version
        ) b
        WHERE
                a.android_device_id <> b.android_device_id
            AND a.android_cpu_abi = b.android_cpu_abi
            AND a.android_manufacturer = b.android_manufacturer
            AND a.android_model = b.android_model
            AND a.android_version = b.android_version
    """)

    op.execute(""" COMMIT """)
    op.execute("""
        TRUNCATE signature_summary_device
    """)
    op.execute(""" COMMIT """)
    now = datetime.date(2013, 9, 10)
    for backfill_date in [
        (now - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            for days in range(1,16)]:
        op.execute("""
            INSERT into signature_summary_device (
                report_date
                , signature_id
                , android_device_id
                , report_count
            )
            WITH android_info AS (
                SELECT
                    reports_clean.signature_id as signature_id
                    , json_object_field_text(raw_crash, 'Android_CPU_ABI') as android_cpu_abi
                    , json_object_field_text(raw_crash, 'Android_Manufacturer') as android_manufacturer
                    , json_object_field_text(raw_crash, 'Android_Model') as android_model
                    , json_object_field_text(raw_crash, 'Android_Version') as android_version
                FROM raw_crashes
                    JOIN reports_clean ON raw_crashes.uuid::text = reports_clean.uuid
                WHERE
                    raw_crashes.date_processed::date = '%(backfill_date)s'
                    AND reports_clean.date_processed::date = '%(backfill_date)s'
            )
            SELECT
                '%(backfill_date)s'::date as report_date
                , signature_id
                , android_device_id
                , count(android_device_id) as report_count
            FROM
                android_info
                JOIN android_devices ON
                    android_info.android_cpu_abi = android_devices.android_cpu_abi
                    AND android_info.android_manufacturer = android_devices.android_manufacturer
                    AND android_info.android_model = android_devices.android_model
                    AND android_info.android_version = android_devices.android_version
            GROUP BY
                report_date, signature_id, android_device_id
        """ % {'backfill_date': backfill_date} )
        op.execute(""" COMMIT """)


def downgrade():
    pass

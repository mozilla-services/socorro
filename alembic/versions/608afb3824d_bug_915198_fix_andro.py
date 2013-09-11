"""bug 915198 fix android devices

Revision ID: 608afb3824d
Revises: 389f5501023b
Create Date: 2013-09-11 08:32:01.500395

"""

# revision identifiers, used by Alembic.
revision = '608afb3824d'
down_revision = '389f5501023b'

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


def downgrade():
    pass

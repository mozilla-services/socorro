"""Fixes bug 959354 - remaining stored proc updates for build_type/update_channel

Revision ID: 514789372d99
Revises: 2c48009040da
Create Date: 2014-01-13 14:43:01.422317

"""

# revision identifiers, used by Alembic.
revision = '514789372d99'
down_revision = '2c48009040da'

import datetime

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    load_stored_proc(op, ['add_new_product.sql',
                          'edit_product_info.sql',
                          'reports_clean_weekly_partition.sql',
                          'update_crash_adu_by_build_signature.sql',
                          'update_crashes_by_user.sql',
                          'update_crashes_by_user_build.sql',
                          'update_home_page_graph.sql',
                          'update_home_page_graph_build.sql',
                          'update_nightly_builds.sql',
                          'update_signatures.sql',
                          'update_tcbs.sql',
                          '001_reports_clean.sql'])

    op.execute(""" DROP FUNCTION backfill_one_day(date) """)

    op.execute("""
        insert into product_build_types (
            SELECT product_name, lower(release_channel)::build_type, throttle
            FROM product_release_channels
        )
    """)
    op.execute(""" COMMIT """)

    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')

    # Backfill reports_clean so that we don't have inconsistent build_type data
    op.execute("""
        SELECT backfill_reports_clean('%s 00:00:00'::timestamptz,
            '%s 00:00:00'::timestamptz + '1 day'::interval)
        """ % (today, today))

def downgrade():
    load_stored_proc(op, ['add_new_product.sql',
                          'backfill_one_day.sql',
                          'edit_product_info.sql',
                          'reports_clean_weekly_partition.sql',
                          'update_crash_adu_by_build_signature.sql',
                          'update_crashes_by_user.sql',
                          'update_crashes_by_user_build.sql',
                          'update_home_page_graph.sql',
                          'update_home_page_graph_build.sql',
                          'update_nightly_builds.sql',
                          'update_signatures.sql',
                          'update_tcbs.sql',
                          '001_reports_clean.sql'])

    op.execute(""" delete from product_build_types """)

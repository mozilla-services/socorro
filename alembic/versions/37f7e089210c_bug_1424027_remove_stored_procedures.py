"""bug 1424027 remove stored procedures

Revision ID: 37f7e089210c
Revises: f4c8c470b67e
Create Date: 2017-12-08 19:22:40.133644

"""

# revision identifiers, used by Alembic.
revision = '37f7e089210c'
down_revision = 'f4c8c470b67e'

from alembic import op
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute("""
    DROP FUNCTION IF EXISTS
    crontabber_nodelete()
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    crontabber_timestamp()
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    find_weekly_partition(date, text)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    get_product_version_ids(citext, citext[])
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    last_record(text)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    log_priorityjobs()
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    pacific2ts(timestamp)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    plugin_count_state(integer, citext, integer)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    socorro_db_data_refresh(timestamp)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    transform_rules_insert_order()
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    transform_rules_update_order()
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_reports_clean_cron(timestamp)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_socorro_db_version(text, date)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    validate_lookup(text, text, text, text)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    watch_report_processing(integer, integer, interval, interval, interval)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    aurora_or_nightly(text)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    check_partitions(text[], integer, integer, text)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    content_count_state(integer, citext, integer)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    crash_madu(bigint, numeric, numeric)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    tstz_between(timestamp, date, date)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    add_column_if_not_exists(text, text, text, boolean, text, text)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    add_old_release(text, text, release_enum, date, boolean)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    create_table_if_not_exists(text, text, text, text[], text[])
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    utc_day_near(timestamp, timestamp)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    daily_crash_code(text, text)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_daily_crashes(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_daily_crashes(date)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    edit_featured_versions(citext, text[])
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_correlations_module(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_final_betas(date)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_all_dups(timestamp, timestamp)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_named_table(text, date)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_reports_duplicates(timestamp, timestamp)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_weekly_report_partitions(date, date, text)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_signature_counts(date, date)
    """)


def downgrade():
    # Not going to do a downgrade because the stored procs are in separate
    # files and this is removing a bunch of stuff I'm 99% sure we don't use. If
    # we need to downgrade, then it's easier to reinstate the files, write a
    # new migration and roll forward.
    pass

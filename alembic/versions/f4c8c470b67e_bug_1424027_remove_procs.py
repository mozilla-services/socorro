"""bug 1424027 remove stored procedures

Revision ID: f4c8c470b67e
Revises: f35c26426066
Create Date: 2017-12-07 21:19:41.454338

This removes a bunch of stored procedures that were used by cron jobs we
removed in May 2017.

"""

# revision identifiers, used by Alembic.
revision = 'f4c8c470b67e'
down_revision = 'f35c26426066'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    # Delete stored procedures
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_crashes_by_user(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_crashes_by_user_build(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_crashes_by_user(date, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_crashes_by_user_build(date, interval)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    update_home_page_graph(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_home_page_graph_build(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_home_page_graph(date, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_home_page_graph_build(date, interval)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    update_exploitability(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_exploitability(date)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_correlations(date)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_correlations_addon(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_correlations_core(date, boolean, interval)
    """)

    op.execute("""
    DROP FUNCTION IF EXISTS
    update_tcbs(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    update_tcbs_build(date, boolean, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_tcbs(date, interval)
    """)
    op.execute("""
    DROP FUNCTION IF EXISTS
    backfill_tcbs_build(date, interval)
    """)

    # Load the new version of backfill_matviews
    load_stored_proc(op, ['backfill_matviews.sql'])


def downgrade():
    # Not going to do a downgrade because the stored procs are in separate
    # files and this is removing a bunch of stuff I'm 99% sure we don't use. If
    # we need to downgrade, then it's easier to reinstate the files, write a
    # new migration and roll forward.
    pass

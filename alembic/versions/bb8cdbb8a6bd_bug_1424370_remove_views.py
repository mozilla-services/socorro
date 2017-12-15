"""bug 1424370 remove views

This removes all the views that we're not using.

Revision ID: bb8cdbb8a6bd
Revises: 37f7e089210c
Create Date: 2017-12-15 23:15:09.014280

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'bb8cdbb8a6bd'
down_revision = '37f7e089210c'


def upgrade():
    # These are used by crashes_by_user_rollup, so have to go first
    op.execute('DROP VIEW IF EXISTS product_crash_ratio')
    op.execute('DROP VIEW IF EXISTS product_os_crash_ratio')

    op.execute('DROP VIEW IF EXISTS crashes_by_user_build_view')
    op.execute('DROP VIEW IF EXISTS crashes_by_user_rollup')
    op.execute('DROP VIEW IF EXISTS crashes_by_user_view')
    op.execute('DROP VIEW IF EXISTS home_page_graph_build_view')
    op.execute('DROP VIEW IF EXISTS home_page_graph_view')
    op.execute('DROP VIEW IF EXISTS performance_check_1')
    op.execute('DROP VIEW IF EXISTS product_selector')


def downgrade():
    # Not going to do a downgrade because the views are in separate files and
    # this is removing a bunch of stuff that isn't used. If we need to
    # downgrade, then it's easier to reinstate the files, write a new migration
    # and roll forward.
    pass

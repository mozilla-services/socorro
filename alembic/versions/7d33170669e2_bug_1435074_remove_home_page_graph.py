"""bug 1435074 remove home_page_graph and home_page_graph_build

Revision ID: 7d33170669e2
Revises: dfead656fe89
Create Date: 2018-04-03 16:34:39.605095

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '7d33170669e2'
down_revision = 'dfead656fe89'


def upgrade():
    op.execute('DROP TABLE IF EXISTS home_page_graph')
    op.execute('DROP TABLE IF EXISTS home_page_graph_build')


def downgrade():
    # There is no going back.
    pass

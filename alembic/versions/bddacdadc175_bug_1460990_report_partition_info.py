"""bug 1460990 report_partition_info

Revision ID: bddacdadc175
Revises: fd76c8bb0d78
Create Date: 2018-05-12 00:42:29.018796

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'bddacdadc175'
down_revision = 'fd76c8bb0d78'


def upgrade():
    op.execute('DROP FUNCTION IF EXISTS drop_named_partitions(date)')
    op.execute('DROP FUNCTION IF EXISTS drop_old_partitions(text, date)')
    op.execute(
        'DROP FUNCTION IF EXISTS weekly_report_partitions(integer, timestamp with time zone)'
    )

    op.execute('DROP TABLE IF EXISTS report_partition_info')


def downgrade():
    pass

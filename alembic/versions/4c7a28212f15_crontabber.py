"""Crontabber state table

Revision ID: 4c7a28212f15
Revises: 523b9e57eba2
Create Date: 2013-10-21 14:10:07.984491

"""

# revision identifiers, used by Alembic.
revision = '4c7a28212f15'
down_revision = '191d0453cc07'

from alembic import op
from socorro.lib import jsontype

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.create_table(
        u'crontabber',
        sa.Column(u'app_name', sa.TEXT(), nullable=False),
        sa.Column(u'next_run', sa.TIMESTAMP(timezone=True)),
        sa.Column(u'first_run', sa.TIMESTAMP(timezone=True)),
        sa.Column(u'last_run', sa.TIMESTAMP(timezone=True)),
        sa.Column(u'last_success', sa.TIMESTAMP(timezone=True)),
        sa.Column(u'error_count', sa.INTEGER(), nullable=False,
                  server_default='0'),
        sa.Column(u'depends_on', postgresql.ARRAY(sa.TEXT())),
        sa.Column(u'last_error', jsontype.JsonType()),
        sa.PrimaryKeyConstraint(u'app_name')
    )
    op.create_index('crontabber_app_name_idx', 'crontabber', ['app_name'])

    op.create_table(
        u'crontabber_log',
        sa.Column(u'id', sa.INTEGER(), nullable=False),
        sa.Column(u'app_name', sa.TEXT(), nullable=False),
        sa.Column(u'log_time', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column(u'success', sa.TIMESTAMP(timezone=True)),
        sa.Column(u'exc_type', sa.TEXT()),
        sa.Column(u'exc_value', sa.TEXT()),
        sa.Column(u'exc_traceback', sa.TEXT()),
        sa.PrimaryKeyConstraint(u'id')
    )
    op.create_index('crontabber_log_app_name_idx',
                    'crontabber_log', ['app_name'])
    op.create_index('crontabber_log_log_time_idx',
                    'crontabber_log', ['log_time'])


def downgrade():
    op.drop_index('crontabber_app_name_idx')
    op.drop_table(u'crontabber')

    op.drop_index('crontabber_log_app_name_idx')
    op.drop_index('crontabber_log_log_time_idx')
    op.drop_table(u'crontabber_log')

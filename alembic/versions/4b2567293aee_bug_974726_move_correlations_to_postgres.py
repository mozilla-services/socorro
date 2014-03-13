"""bug 974726 - move correlations to postgres

Revision ID: 4b2567293aee
Revises: 74d6fd90b59
Create Date: 2014-03-10 11:43:52.585210

"""

# revision identifiers, used by Alembic.
revision = '4b2567293aee'
down_revision = '74d6fd90b59'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column




def upgrade():
    load_stored_proc(op, ['backfill_matviews.sql',
                          'update_correlations_addon.sql',
                          'update_correlations_core.sql',
                          'update_correlations_module.sql'])
    op.create_table(u'correlations_core',
    sa.Column(u'product_version_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column(u'cpu_arch', sa.TEXT(), nullable=False),
    sa.Column(u'cpu_count', sa.TEXT(), nullable=False),
    sa.Column(u'report_date', sa.DATE(), nullable=False),
    sa.Column(u'os_name', sa.TEXT(), nullable=False),
    sa.Column(u'signature_id', sa.INTEGER(), nullable=False),
    sa.Column(u'total', sa.BIGINT(), nullable=True)
    )
    op.create_index('ix_correlations_core_report_date', 'correlations_core', [u'report_date'], unique=False)
    op.create_index('ix_correlations_core_signature_id', 'correlations_core', [u'signature_id'], unique=False)
    sa.Column(u'version_num', sa.VARCHAR(length=32), nullable=False)
    op.create_table(u'correlations_addon',
    sa.Column(u'product_version_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column(u'addon_id', sa.TEXT(), nullable=False),
    sa.Column(u'addon_version', sa.TEXT(), nullable=False),
    sa.Column(u'report_date', sa.DATE(), nullable=False),
    sa.Column(u'os_name', sa.TEXT(), nullable=False),
    sa.Column(u'signature_id', sa.INTEGER(), nullable=False),
    sa.Column(u'total', sa.BIGINT(), nullable=True)
    )
    op.create_index('ix_correlations_addon_report_date', 'correlations_addon', [u'report_date'], unique=False)
    op.create_index('ix_correlations_addon_signature_id', 'correlations_addon', [u'signature_id'], unique=False)
    op.create_table(u'correlations_module',
    sa.Column(u'product_version_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column(u'module_name', sa.TEXT(), nullable=False),
    sa.Column(u'module_version', sa.TEXT(), nullable=False),
    sa.Column(u'report_date', sa.DATE(), nullable=False),
    sa.Column(u'os_name', sa.TEXT(), nullable=False),
    sa.Column(u'signature_id', sa.INTEGER(), nullable=False),
    sa.Column(u'total', sa.BIGINT(), nullable=True)
    )
    op.create_index('ix_correlations_module_report_date', 'correlations_module', [u'report_date'], unique=False)
    op.create_index('ix_correlations_module_signature_id', 'correlations_module', [u'signature_id'], unique=False)
    op.drop_table(u'correlation_modules')
    op.drop_table(u'correlation_cores')
    op.drop_table(u'correlation_addons')
    op.drop_table(u'correlations')
    op.execute("""
        DROP FUNCTION update_correlations(date, boolean, interval)
    """)

def downgrade():
    load_stored_proc(op, ['backfill_matviews.sql',
                          'update_correlations_addon.sql',
                          'update_correlations_core.sql',
                          'update_correlations_module.sql'])
    op.drop_index('ix_correlations_module_signature_id', table_name='correlations_module')
    op.drop_index('ix_correlations_module_report_date', table_name='correlations_module')
    op.drop_table(u'correlations_module')
    op.drop_index('ix_correlations_addon_signature_id', table_name='correlations_addon')
    op.drop_index('ix_correlations_addon_report_date', table_name='correlations_addon')
    op.drop_table(u'correlations_addon')
    op.drop_index('ix_correlations_core_signature_id', table_name='correlations_core')
    op.drop_index('ix_correlations_core_report_date', table_name='correlations_core')
    op.drop_table(u'correlations_core')
    op.create_table(u'correlation_cores', sa.Column(u'dummy', sa.TEXT(), nullable=False))
    op.create_table(u'correlation_modules', sa.Column(u'dummy', sa.TEXT(), nullable=False))
    op.create_table(u'correlation_addons', sa.Column(u'dummy', sa.TEXT(), nullable=False))
    op.create_table(u'correlations', sa.Column(u'dummy', sa.TEXT(), nullable=False))


"""delete unused tables

Revision ID: 8e8390138426
Revises: c50669ec885e
Create Date: 2018-04-17 00:57:11.902688

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '8e8390138426'
down_revision = 'c50669ec885e'


def upgrade():
    # Bug 1435070 - remove reprocessing_jobs
    op.execute('DROP TABLE IF EXISTS reprocessing_jobs')

    # Bug 1435072 - remove priorityjobs, priorityjobs_log, and
    # priorityjobs_logging_switch
    op.execute('DROP TABLE IF EXISTS priorityjobs')
    op.execute('DROP TABLE IF EXISTS priorityjobs_log')
    op.execute('DROP TABLE IF EXISTS priorityjobs_logging_switch')

    # Bug 1435076 - remove correlations, correlations_addon, correlations_core,
    # correlations_module
    op.execute('DROP TABLE IF EXISTS correlations')
    op.execute('DROP TABLE IF EXISTS correlations_addon')
    op.execute('DROP TABLE IF EXISTS correlations_core')
    op.execute('DROP TABLE IF EXISTS correlations_module')


def downgrade():
    pass

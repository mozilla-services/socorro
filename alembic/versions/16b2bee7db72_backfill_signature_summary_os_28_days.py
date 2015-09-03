"""backfill signature_summary_os 28 days

Revision ID: 16b2bee7db72
Revises: 4afd4e13281d
Create Date: 2015-09-02 13:53:13.505082

"""
import datetime

# revision identifiers, used by Alembic.
revision = '16b2bee7db72'
down_revision = '4afd4e13281d'

from alembic import op


def upgrade():
    # We only ever, at most, show 28 days in the report list that
    # shows this signature summary.
    today = datetime.datetime.utcnow().date()
    for i in range(28, 0, -1):
        then = today - datetime.timedelta(days=i)
        till = then + datetime.timedelta(days=1)
        op.execute(
            """
            SELECT
                backfill_weekly_report_partitions(
                    '%s', '%s', 'signature_summary_os'
                )
            """ % (
                then.strftime('%Y-%m-%d'),
                till.strftime('%Y-%m-%d')
            )
        )
        op.execute(
            """
            SELECT
                update_signature_summary_os('%s')
            """ % (
                then.strftime('%Y-%m-%d'),
            )
        )
        op.execute('COMMIT')


def downgrade():
    pass

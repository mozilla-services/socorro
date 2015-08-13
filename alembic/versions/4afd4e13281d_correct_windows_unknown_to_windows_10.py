"""correct 'Windows Unknown' records

Revision ID: 4afd4e13281d
Revises: b99155654de
Create Date: 2015-08-13 13:42:53.101703

Aims to solve: https://bugzilla.mozilla.org/show_bug.cgi?id=1132652
which was re-opened.
"""
import datetime

# revision identifiers, used by Alembic.
revision = '4afd4e13281d'
down_revision = 'b99155654de'

from alembic import op


def upgrade():
    # The function `create_os_version_string` gets used by
    # `procs/update_os_versions.sql` but re-running it won't fix those
    # that have been stored as "Windows Unknown" because the os_name is not
    # null. So let's correct that.
    op.execute("""
        UPDATE os_versions
        SET
        os_version_string = 'Windows 10'
        WHERE
        os_name = 'Windows' AND
        major_version = 10 AND
        os_version_string = 'Windows Unknown'
    """)

    backfill_signature_summary_os()


def backfill_signature_summary_os():
    # We only ever, at most, show 28 days in the report list that
    # shows this signature summary.
    op.execute("""
        TRUNCATE signature_summary_os
    """)
    op.execute('COMMIT')

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
        op.execute('COMMIT')


def downgrade():
    op.execute("""
        UPDATE os_versions
        SET os_version_string = 'Windows Unknown'
        WHERE
        os_version_string = 'Windows 10' AND
        os_name = 'Windows' AND
        major_version = 10
    """)

    backfill_signature_summary_os()

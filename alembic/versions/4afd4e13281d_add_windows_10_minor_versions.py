"""correct 'Windows Unknown' records

Revision ID: 4afd4e13281d
Revises: b99155654de
Create Date: 2015-08-13 13:42:53.101703

Aims to solve: https://bugzilla.mozilla.org/show_bug.cgi?id=1132652
which was re-opened.
"""

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

    # The reason for doing all of this is because the
    # `update_signature_summary_os` stored procedure (in
    # `procs/update_signature_summary_os.sql`) generates an aggreate summary
    # of crashes per OS. That one is backfill based meaning crontabber can
    # auto-heal but there's really no good way of re-running it for all
    # past computations. Instead of re-running those, let's just fix it
    # straight away.
    op.execute("""
        UPDATE signature_summary_os
        SET
        os_version_string = 'Windows 10'
        WHERE
        os_version_string = 'Windows Unknown'
    """)


def downgrade():
    op.execute("""
        UPDATE os_versions
        SET os_version_string = 'Windows Unknown'
        WHERE
        os_version_string = 'Windows 10' AND
        os_name = 'Windows' AND
        major_version = 10
    """)

    op.execute("""
        UPDATE signature_summary_os
        SET
        os_version_string = 'Windows Unknown'
        WHERE
        os_version_string = 'Windows 10'
    """)

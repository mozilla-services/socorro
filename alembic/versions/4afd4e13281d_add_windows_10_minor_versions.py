"""add windows 10 minor versions

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
    # table `windows_versions` is the source that is used to help populate
    # the `os_version_string` column in table `os_versions`.
    # See `procs/create_os_version_string.sql`
    op.execute("""
        INSERT INTO windows_versions
        (windows_version_name, major_version, minor_version) VALUES
        ('Windows 10', 10, 4),
        ('Windows 10', 10, 5)
    """)

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
        (minor_version = 4 OR minor_version = 5)
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
        DELETE FROM windows_versions
        WHERE
        windows_version_name = 'Windows 10' AND
        major_version = 10 AND
        (minor_version = 4 OR minor_version = 5)
    """)

    op.execute("""
        UPDATE os_versions
        SET os_version_string = 'Windows Unknown'
        WHERE
        os_version_string = 'Windows 10' AND
        os_name = 'Windows' AND
        major_version = 10 AND
        (minor_version = 4 OR minor_version = 5)
    """)

    op.execute("""
        UPDATE signature_summary_os
        SET
        os_version_string = 'Windows Unknown'
        WHERE
        os_version_string = 'Windows 10'
    """)

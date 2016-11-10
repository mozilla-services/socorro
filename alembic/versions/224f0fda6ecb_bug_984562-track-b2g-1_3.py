"""bug 984562 - track b2g 1.3

Revision ID: 224f0fda6ecb
Revises: 4c279bec76d8
Create Date: 2014-03-28 10:54:59.521434

"""

# revision identifiers, used by Alembic.
revision = '224f0fda6ecb'
down_revision = '4c279bec76d8'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    op.execute("""
        INSERT INTO update_channel_map
        (update_channel, productid, version_field, rewrite)
        VALUES
        ('hamachi/1.3.0/nightly',
         '{3c2e2abc-06d4-11e1-ac3b-374f68613e61}',
         'B2G_OS_Version',
         '{"Android_Manufacturer": "unknown",
           "Android_Model": "msm7627a",
           "Android_Version": "15(REL)",
           "B2G_OS_Version": "1.3.0.0-prerelease",
           "BuildID":
                ["20140317004001"],
            "ProductName": "B2G",
            "ReleaseChannel": "hamachi/1.3.0/nightly",
            "Version": "28.0",
            "rewrite_update_channel_to": "release-buri",
            "rewrite_build_type_to": "release"}'
        )
    """)
    op.execute("""
        INSERT INTO update_channel_map
        (update_channel, productid, version_field, rewrite)
        VALUES
        ('default',
         '{3c2e2abc-06d4-11e1-ac3b-374f68613e61}',
         'B2G_OS_Version',
         '{"Android_Manufacturer": "Spreadtrum",
           "Android_Model": "sp6821a",
           "Android_Version": "15(AOSP)",
           "B2G_OS_Version": "1.3.0.0-prerelease",
           "BuildID":
                ["20140317060055"],
            "ProductName": "B2G",
            "ReleaseChannel": "default",
            "Version": "28.0",
            "rewrite_update_channel_to": "release-tarako",
            "rewrite_build_type_to": "release"}'
        )
    """)

def downgrade():
    op.execute("""
        DELETE FROM update_channel_map
        WHERE rewrite->>'rewrite_update_channel_to' = 'release-buri'
        OR rewrite->>'rewrite_update_channel_to' = 'release-tarako'
    """)

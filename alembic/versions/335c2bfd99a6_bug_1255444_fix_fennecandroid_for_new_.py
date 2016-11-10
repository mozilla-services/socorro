"""bug 1255444 fix fennecandroid for new release repository

Revision ID: 335c2bfd99a6
Revises: 9371b45451b
Create Date: 2016-03-10 13:24:35.662063

"""

# revision identifiers, used by Alembic.
revision = '335c2bfd99a6'
down_revision = '9371b45451b'

from alembic import op
from socorro.lib import citexttype, jsontype, buildtype
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

def upgrade():
    op.execute("""
      INSERT INTO release_repositories VALUES ('mozilla-central-android-api-15');
      INSERT INTO release_repositories VALUES ('mozilla-aurora-android-api-15');
      INSERT INTO release_repositories VALUES ('mozilla-beta-android-api-15');
      INSERT INTO release_repositories VALUES ('mozilla-release-android-api-15');
      INSERT INTO special_product_platforms (platform, repository, release_channel, release_name, product_name, min_version) VALUES ('android-arm', 'mozilla-central-android-api-15', 'nightly', 'mobile', 'FennecAndroid', '37.0');
      INSERT INTO special_product_platforms (platform, repository, release_channel, release_name, product_name, min_version) VALUES ('android-arm', 'mozilla-aurora-android-api-15', 'aurora', 'mobile', 'FennecAndroid', '37.0');
      INSERT INTO special_product_platforms (platform, repository, release_channel, release_name, product_name, min_version) VALUES ('android-arm', 'mozilla-beta-android-api-15', 'beta', 'mobile', 'FennecAndroid', '37.0');
      INSERT INTO special_product_platforms (platform, repository, release_channel, release_name, product_name, min_version) VALUES ('android-arm', 'mozilla-release-android-api-15', 'release', 'mobile', 'FennecAndroid', '37.0');
    """)

def downgrade():
    op.execute("""
      DELETE FROM release_repositories WHERE repository = 'mozilla-central-android-api-15';
      DELETE FROM release_repositories WHERE repository = 'mozilla-aurora-android-api-15';
      DELETE FROM release_repositories WHERE repository = 'mozilla-beta-android-api-15';
      DELETE FROM release_repositories WHERE repository = 'mozilla-release-android-api-15';
      DELETE FROM special_product_platforms WHERE platform = 'android-arm' AND repository = 'mozilla-central-android-api-15' AND release_channel = 'nightly' AND release_name = 'mobile' AND product_name = 'FennecAndroid' AND min_version = '37.0';
      DELETE FROM special_product_platforms WHERE platform = 'android-arm' AND repository = 'mozilla-aurora-android-api-15' AND release_channel = 'aurora' AND release_name = 'mobile' AND product_name = 'FennecAndroid' AND min_version = '37.0';
      DELETE FROM special_product_platforms WHERE platform = 'android-arm' AND repository = 'mozilla-beta-android-api-15' AND release_channel = 'beta' AND release_name = 'mobile' AND product_name = 'FennecAndroid' AND min_version = '37.0';
      DELETE FROM special_product_platforms WHERE platform = 'android-arm' AND repository = 'mozilla-release-android-api-15' AND release_channel = 'release' AND release_name = 'mobile' AND product_name = 'FennecAndroid' AND min_version = '37.0';
    """)

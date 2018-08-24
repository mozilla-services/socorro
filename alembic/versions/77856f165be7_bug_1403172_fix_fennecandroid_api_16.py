"""bug 1403172 fix fennecandroid api 16

Revision ID: 77856f165be7
Revises: a38b03765a79
Create Date: 2017-09-28 20:41:56.221487

"""

# revision identifiers, used by Alembic.
revision = '77856f165be7'
down_revision = 'a38b03765a79'

from alembic import op
from socorro.lib.migrations import fix_permissions, load_stored_proc

import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column


def upgrade():
    op.execute("""
    INSERT INTO release_repositories VALUES ('mozilla-central-android-api-16');
    INSERT INTO release_repositories VALUES ('mozilla-beta-android-api-16');
    INSERT INTO release_repositories VALUES ('mozilla-release-android-api-16');
    INSERT INTO special_product_platforms
        (platform, repository, release_channel, release_name, product_name, min_version)
    VALUES
        ('android-arm', 'mozilla-central-android-api-16', 'nightly', 'mobile', 'FennecAndroid', '37.0');
    INSERT INTO special_product_platforms
        (platform, repository, release_channel, release_name, product_name, min_version)
    VALUES
        ('android-arm', 'mozilla-beta-android-api-16', 'beta', 'mobile', 'FennecAndroid', '37.0');
    INSERT INTO special_product_platforms
        (platform, repository, release_channel, release_name, product_name, min_version)
    VALUES
        ('android-arm', 'mozilla-release-android-api-16', 'release', 'mobile', 'FennecAndroid', '37.0');
    """)


def downgrade():
    op.execute("""
    DELETE FROM release_repositories WHERE repository = 'mozilla-central-android-api-16';
    DELETE FROM release_repositories WHERE repository = 'mozilla-beta-android-api-16';
    DELETE FROM release_repositories WHERE repository = 'mozilla-release-android-api-16';
    DELETE FROM special_product_platforms
    WHERE
        platform = 'android-arm'
        AND repository = 'mozilla-central-android-api-16'
        AND release_channel = 'nightly'
        AND release_name = 'mobile'
        AND product_name = 'FennecAndroid'
        AND min_version = '37.0';
    DELETE FROM special_product_platforms
    WHERE
        platform = 'android-arm'
        AND repository = 'mozilla-beta-android-api-16'
        AND release_channel = 'beta'
        AND release_name = 'mobile'
        AND product_name = 'FennecAndroid'
        AND min_version = '37.0';
    DELETE FROM special_product_platforms
    WHERE
        platform = 'android-arm'
        AND repository = 'mozilla-release-android-api-16'
        AND release_channel = 'release'
        AND release_name = 'mobile'
        AND product_name = 'FennecAndroid'
        AND min_version = '37.0';
    """)

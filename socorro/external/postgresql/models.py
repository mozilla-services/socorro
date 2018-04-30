#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
SQLAlchemy models for Socorro
"""
from __future__ import unicode_literals

from sqlalchemy import Column, ForeignKey, Index, text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import sqlalchemy.types as types

from sqlalchemy.dialects.postgresql import (
    INTERVAL,
    INTEGER,
    TEXT,
    TIMESTAMP,
    NUMERIC,
    DATE,
    BOOLEAN,
    UUID,
    VARCHAR,
    ARRAY,
    BIGINT,
    SMALLINT,
)
from sqlalchemy.dialects.postgresql.base import ischema_names


#######################################
# Create CITEXT type for SQL Alchemy
#######################################
class CITEXT(types.UserDefinedType):
    name = 'citext'

    def get_col_spec(self):
        return 'CITEXT'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return "citext"


class JSON(types.UserDefinedType):
    name = 'json'

    def get_col_spec(self):
        return 'JSON'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return "json"


class MAJOR_VERSION(types.UserDefinedType):
    name = 'MAJOR_VERSION'

    def get_col_spec(self):
        return 'MAJOR_VERSION'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return 'major_version'


class flash_process_dump_type(types.UserDefinedType):
    name = 'flash_process_dump_type'

    def get_col_spec(self):
        return 'flash_process_dump_type'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return 'flash_process_dump_type'


class product_info_change(types.UserDefinedType):
    name = 'product_info_change'

    def get_col_spec(self):
        return 'product_info_change'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return 'product_info_change'


class release_enum(types.UserDefinedType):
    name = 'release_enum'

    def get_col_spec(self):
        return 'release_enum'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return 'release_enum'


class build_type(types.UserDefinedType):
    name = 'build_type'

    def get_col_spec(self):
        return 'build_type'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return 'build_type'


class build_type_enum(types.UserDefinedType):
    name = 'build_type_enum'

    def get_col_spec(self):
        return 'build_type_enum'

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

    def __repr__(self):
        return 'build_type_enum'


###########################################
# Baseclass for all Socorro tables
###########################################

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata

ischema_names['citext'] = CITEXT
ischema_names['json'] = JSON
ischema_names['major_version'] = MAJOR_VERSION
ischema_names['release_enum'] = release_enum
ischema_names['product_info_change'] = product_info_change
ischema_names['flash_process_dump_type'] = flash_process_dump_type
ischema_names['build_type'] = build_type
ischema_names['build_type_enum'] = build_type_enum


###############################
# Schema definition: Tables
###############################


class RawAdiLogs(DeclarativeBase):
    __tablename__ = 'raw_adi_logs'

    # column definitions
    report_date = Column(u'report_date', DATE())
    product_name = Column(u'product_name', TEXT())
    product_os_platform = Column(u'product_os_platform', TEXT())
    product_os_version = Column(u'product_os_version', TEXT())
    product_version = Column(u'product_version', TEXT())
    build = Column(u'build', TEXT())
    build_channel = Column(u'build_channel', TEXT())
    product_guid = Column(u'product_guid', TEXT())
    count = Column(u'count', INTEGER())

    __mapper_args__ = {"primary_key": (
        report_date,
        product_name,
        product_os_platform,
        product_os_version,
        product_version,
        build,
        build_channel,
        product_guid,
        count
    )}


class RawAdi(DeclarativeBase):
    __tablename__ = 'raw_adi'

    # column definitions
    adi_count = Column(u'adi_count', INTEGER())
    date = Column(u'date', DATE())
    product_name = Column(u'product_name', TEXT())
    product_os_platform = Column(u'product_os_platform', TEXT())
    product_os_version = Column(u'product_os_version', TEXT())
    product_version = Column(u'product_version', TEXT())
    build = Column(u'build', TEXT())
    product_guid = Column(u'product_guid', TEXT())
    update_channel = Column(u'update_channel', TEXT())
    received_at = Column(u'received_at', TIMESTAMP(
        timezone=True), server_default=text('NOW()'))

    __mapper_args__ = {
        "primary_key": (
            adi_count, date, product_name, product_version,
            product_os_platform, product_os_version, build, product_guid, update_channel
        )
    }
    __table_args__ = (
        Index(u'raw_adi_1_idx', date, product_name, product_version,
              product_os_platform, product_os_version),
    )


class ReportsBad(DeclarativeBase):
    __tablename__ = 'reports_bad'
    uuid = Column(u'uuid', TEXT(), nullable=False)
    date_processed = Column(u'date_processed', TIMESTAMP(
        timezone=True), nullable=False)

    __mapper_args__ = {"primary_key": (uuid)}


class WindowsVersion(DeclarativeBase):
    __tablename__ = 'windows_versions'
    windows_version_name = Column(
        u'windows_version_name', CITEXT(), nullable=False)
    major_version = Column(u'major_version', INTEGER(), nullable=False)
    minor_version = Column(u'minor_version', INTEGER(), nullable=False)

    __mapper_args__ = {"primary_key": (major_version, minor_version)}
    __table_args__ = (
        Index('windows_version_key', major_version, minor_version, unique=True),
    )


class Report(DeclarativeBase):
    __tablename__ = 'reports'

    __table_args__ = {}

    # Column definitions
    id = Column(u'id', Integer(), primary_key=True)
    client_crash_date = Column(u'client_crash_date', TIMESTAMP(timezone=True))
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True))
    uuid = Column(u'uuid', VARCHAR(length=50), nullable=False)
    product = Column(u'product', VARCHAR(length=30))
    version = Column(u'version', VARCHAR(length=16))
    build = Column(u'build', VARCHAR(length=30))
    signature = Column(u'signature', VARCHAR(length=255))
    url = Column(u'url', VARCHAR(length=255))
    install_age = Column(u'install_age', INTEGER())
    last_crash = Column(u'last_crash', INTEGER())
    uptime = Column(u'uptime', INTEGER())
    cpu_name = Column(u'cpu_name', VARCHAR(length=100))
    cpu_info = Column(u'cpu_info', VARCHAR(length=100))
    reason = Column(u'reason', VARCHAR(length=255))
    address = Column(u'address', VARCHAR(length=20))
    os_name = Column(u'os_name', VARCHAR(length=100))
    os_version = Column(u'os_version', VARCHAR(length=100))
    email = Column(u'email', VARCHAR(length=100))
    user_id = Column(u'user_id', VARCHAR(length=50))
    started_datetime = Column(u'started_datetime', TIMESTAMP(timezone=True))
    completed_datetime = Column(
        u'completed_datetime', TIMESTAMP(timezone=True))
    success = Column(u'success', BOOLEAN())
    truncated = Column(u'truncated', BOOLEAN())
    processor_notes = Column(u'processor_notes', TEXT())
    user_comments = Column(u'user_comments', VARCHAR(length=1024))
    app_notes = Column(u'app_notes', VARCHAR(length=1024))
    distributor = Column(u'distributor', VARCHAR(length=20))
    distributor_version = Column(u'distributor_version', VARCHAR(length=20))
    topmost_filenames = Column(u'topmost_filenames', TEXT())
    addons_checked = Column(u'addons_checked', BOOLEAN())
    flash_version = Column(u'flash_version', TEXT())
    hangid = Column(u'hangid', TEXT())
    process_type = Column(u'process_type', TEXT())
    release_channel = Column(u'release_channel', TEXT())  # DEPRECATED
    productid = Column(u'productid', TEXT())
    exploitability = Column(u'exploitability', TEXT())
    # Replaces release_channel
    update_channel = Column(u'update_channel', TEXT())


class Address(DeclarativeBase):
    __tablename__ = 'addresses'

    # column definitions
    address_id = Column(u'address_id', INTEGER(),
                        primary_key=True, nullable=False)
    address = Column(u'address', CITEXT(), nullable=False,
                     index=True, unique=True)
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))


class AlembicVersion(DeclarativeBase):
    __tablename__ = 'alembic_version'

    # column definitions
    version_num = Column(u'version_num', VARCHAR(length=32), nullable=False)

    # relationship definitions
    __mapper_args__ = {"primary_key": (version_num)}


class BugAssociation(DeclarativeBase):
    __tablename__ = 'bug_associations'

    # column definitions
    bug_id = Column(u'bug_id', INTEGER(), primary_key=True,
                    nullable=False, index=True)
    signature = Column(u'signature', TEXT(), primary_key=True, nullable=False)


class BuildAdu(DeclarativeBase):
    __tablename__ = 'build_adu'

    # column definitions
    product_version_id = Column(u'product_version_id', INTEGER(),
                                primary_key=True, nullable=False, autoincrement=False)
    build_date = Column(u'build_date', DATE(),
                        primary_key=True, nullable=False)
    adu_date = Column(u'adu_date', DATE(), primary_key=True, nullable=False)
    os_name = Column(u'os_name', CITEXT(), primary_key=True, nullable=False)
    adu_count = Column(u'adu_count', INTEGER(), nullable=False)

    __table_args__ = (
        Index('build_adu_key', product_version_id,
              build_date, adu_date, os_name, unique=True),
    )


class Domain(DeclarativeBase):
    __tablename__ = 'domains'

    # column definitions
    domain = Column(u'domain', CITEXT(), nullable=False,
                    index=True, unique=True)
    domain_id = Column(u'domain_id', INTEGER(),
                       primary_key=True, nullable=False)
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))


class FlashVersion(DeclarativeBase):
    __tablename__ = 'flash_versions'

    # column definitions
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))
    flash_version = Column(u'flash_version', CITEXT(),
                           nullable=False, index=True)
    flash_version_id = Column(
        u'flash_version_id', INTEGER(), primary_key=True, nullable=False)


class OsName(DeclarativeBase):
    __tablename__ = 'os_names'

    # column definitions
    os_name = Column(u'os_name', CITEXT(), primary_key=True, nullable=False)
    os_short_name = Column(u'os_short_name', CITEXT(), nullable=False)


class OsNameMatche(DeclarativeBase):
    __tablename__ = 'os_name_matches'

    # column definitions
    match_string = Column(u'match_string', TEXT(),
                          primary_key=True, nullable=False)
    os_name = Column(u'os_name', CITEXT(), ForeignKey(
        'os_names.os_name'), primary_key=True, nullable=False)

    __table_args__ = (
        Index('os_name_matches_key', os_name, match_string, unique=True),
    )

    # relationship definitions
    os_names = relationship(
        'OsName', primaryjoin='OsNameMatche.os_name==OsName.os_name')


class OsVersion(DeclarativeBase):
    __tablename__ = 'os_versions'

    # column definitions
    major_version = Column(u'major_version', INTEGER(), nullable=False)
    minor_version = Column(u'minor_version', INTEGER(), nullable=False)
    os_name = Column(u'os_name', CITEXT(), ForeignKey(
        'os_names.os_name'), nullable=False)
    os_version_id = Column(u'os_version_id', INTEGER(),
                           primary_key=True, nullable=False)
    os_version_string = Column(u'os_version_string', CITEXT())

    # relationship definitions
    os_names = relationship(
        'OsName', primaryjoin='OsVersion.os_name==OsName.os_name')


class Product(DeclarativeBase):
    __tablename__ = 'products'

    # column definitions
    product_name = Column(u'product_name', CITEXT(),
                          primary_key=True, nullable=False)
    rapid_beta_version = Column(u'rapid_beta_version', MAJOR_VERSION())
    rapid_release_version = Column(u'rapid_release_version', MAJOR_VERSION())
    release_name = Column(u'release_name', CITEXT(), nullable=False)
    sort = Column(u'sort', SMALLINT(), nullable=False,
                  server_default=text('0'))

    # relationship definitions
    release_channels = relationship(
        'ReleaseChannel',
        primaryjoin='Product.product_name==ProductReleaseChannel.product_name',
        secondary='ProductReleaseChannel',
        secondaryjoin='ProductReleaseChannel.release_channel==ReleaseChannel.release_channel'
    )  # DEPRECATED
    product_versions = relationship(
        'Product',
        primaryjoin='Product.product_name==ProductVersion.product_name',
        secondary='ProductVersion',
        secondaryjoin='ProductVersion.rapid_beta_id==ProductVersion.product_version_id'
    )
    signatures = relationship(
        'Signature',
        primaryjoin='Product.product_name==SignatureProductsRollup.product_name',
        secondary='SignatureProductsRollup',
        secondaryjoin='SignatureProductsRollup.signature_id==Signature.signature_id'
    )


class ProductAdu(DeclarativeBase):
    __tablename__ = 'product_adu'

    # column definitions
    adu_count = Column(u'adu_count', BIGINT(),
                       nullable=False, server_default=text('0'))
    adu_date = Column(u'adu_date', DATE(), primary_key=True, nullable=False)
    os_name = Column(u'os_name', CITEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(),
                                primary_key=True, nullable=False, autoincrement=False)


class ProductProductidMap(DeclarativeBase):
    __tablename__ = 'product_productid_map'

    # column definitions
    product_name = Column(u'product_name', CITEXT(), ForeignKey(
        'products.product_name'), nullable=False)
    productid = Column(u'productid', TEXT(), primary_key=True, nullable=False)
    rewrite = Column(u'rewrite', BOOLEAN(), nullable=False,
                     server_default=text('False'))
    version_began = Column(u'version_began', MAJOR_VERSION())
    version_ended = Column(u'version_ended', MAJOR_VERSION())

    __table_args__ = (
        Index('productid_map_key2', product_name, version_began, unique=True),
    )

    # relationship definitions
    products = relationship(
        'Product',
        primaryjoin='ProductProductidMap.product_name==Product.product_name'
    )


# DEPRECATED -> ProductBuildType
class ProductReleaseChannel(DeclarativeBase):
    __tablename__ = 'product_release_channels'

    # column definitions
    product_name = Column(u'product_name', CITEXT(), ForeignKey(
        'products.product_name'), primary_key=True, nullable=False)
    release_channel = Column(u'release_channel', CITEXT(), ForeignKey(
        'release_channels.release_channel'), primary_key=True, nullable=False)
    throttle = Column(u'throttle', NUMERIC(), nullable=False,
                      server_default=text('1.0'))

    # relationship definitions
    release_channels = relationship(
        'ReleaseChannel',
        primaryjoin='ProductReleaseChannel.release_channel==ReleaseChannel.release_channel'
    )
    products = relationship(
        'Product',
        primaryjoin='ProductReleaseChannel.product_name==Product.product_name'
    )


class ProductBuildType(DeclarativeBase):
    """ Human-defined list of build_types, mapped to product names;
    includes processing throttle setting """
    __tablename__ = 'product_build_types'

    # column definitions
    product_name = Column(u'product_name', CITEXT(), ForeignKey(
        'products.product_name'), primary_key=True, nullable=False)
    build_type = Column(build_type(), primary_key=True, nullable=False)
    throttle = Column(u'throttle', NUMERIC(), nullable=False,
                      server_default=text('1.0'))

    # relationship definitions
    products = relationship(
        'Product', primaryjoin='ProductBuildType.product_name==Product.product_name')


class ProductVersion(DeclarativeBase):
    __tablename__ = 'product_versions'

    # column definitions
    product_version_id = Column(
        u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    product_name = Column(u'product_name', CITEXT(), ForeignKey(
        'products.product_name'), nullable=False, index=True)
    major_version = Column(u'major_version', MAJOR_VERSION(), index=True)
    release_version = Column(u'release_version', CITEXT(), nullable=False)
    version_string = Column(u'version_string', CITEXT(), nullable=False)
    beta_number = Column(u'beta_number', INTEGER())
    version_sort = Column(u'version_sort', TEXT(),
                          nullable=False, server_default="0", index=True)
    build_date = Column(u'build_date', DATE(), nullable=False)
    sunset_date = Column(u'sunset_date', DATE(), nullable=False)
    featured_version = Column(u'featured_version', BOOLEAN(
    ), nullable=False, server_default=text('False'))
    build_type = Column(u'build_type', CITEXT(), nullable=False,
                        server_default='release')  # DEPRECATED
    has_builds = Column(u'has_builds', BOOLEAN())
    is_rapid_beta = Column(u'is_rapid_beta', BOOLEAN(),
                           server_default=text('False'))
    rapid_beta_id = Column(u'rapid_beta_id', INTEGER(), ForeignKey(
        'product_versions.product_version_id'))
    build_type_enum = Column(u'build_type_enum', build_type_enum())
    # Above is a transition definition.
    # We will rename build_type_enum to build_type once old CITEXT column
    # is fully deprecated, also make this part of the primary key later. It
    # will look like this:
    # build_type = Column(
    #    u'build_type_enum', build_type_enum(), nullable=False, server_default='release')
    version_build = Column(u'version_build', TEXT())  # Replaces 'beta_number'

    __table_args__ = (
        Index('product_version_version_key',
              product_name, version_string, unique=True),
    )

    # relationship definitions
    products = relationship(
        'Product',
        primaryjoin='ProductVersion.product_version_id==ProductVersion.rapid_beta_id',
        secondary='ProductVersion',
        secondaryjoin='ProductVersion.product_name==Product.product_name'
    )
    product_versions = relationship(
        'ProductVersion',
        primaryjoin='ProductVersion.rapid_beta_id==ProductVersion.product_version_id'
    )


class ProductVersionBuild(DeclarativeBase):
    __tablename__ = 'product_version_builds'

    # column definitions
    build_id = Column(u'build_id', NUMERIC(), primary_key=True, nullable=False)
    platform = Column(u'platform', TEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), ForeignKey(
        'product_versions.product_version_id'), primary_key=True, nullable=False)
    repository = Column(u'repository', CITEXT())

    # relationship definitions
    product_versions = relationship(
        'ProductVersion',
        primaryjoin='ProductVersionBuild.product_version_id==ProductVersion.product_version_id'
    )


class RawCrashes(DeclarativeBase):
    __tablename__ = 'raw_crashes'

    # column definitions
    uuid = Column(u'uuid', UUID(), nullable=False, index=True, unique=True)
    raw_crash = Column(u'raw_crash', JSON(), nullable=False)
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True))

    # relationship definitions
    __mapper_args__ = {"primary_key": (uuid)}


class Reason(DeclarativeBase):
    __tablename__ = 'reasons'

    # column definitions
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))
    reason = Column(u'reason', CITEXT(), nullable=False,
                    index=True, unique=True)
    reason_id = Column(u'reason_id', INTEGER(),
                       primary_key=True, nullable=False)

    # relationship definitions


# DEPRECATED -> build_type ENUM
class ReleaseChannel(DeclarativeBase):
    __tablename__ = 'release_channels'

    # column definitions
    release_channel = Column(u'release_channel', CITEXT(),
                             primary_key=True, nullable=False)
    sort = Column(u'sort', SMALLINT(), nullable=False,
                  server_default=text('0'))

    # relationship definitions
    products = relationship(
        'Product',
        primaryjoin='ReleaseChannel.release_channel==ProductReleaseChannel.release_channel',
        secondary='ProductReleaseChannel',
        secondaryjoin='ProductReleaseChannel.product_name==Product.product_name'
    )


class ReleaseRepository(DeclarativeBase):
    __tablename__ = 'release_repositories'

    # column definitions
    repository = Column(u'repository', CITEXT(),
                        primary_key=True, nullable=False)


class ReleasesRaw(DeclarativeBase):
    __tablename__ = 'releases_raw'

    # column definitions
    beta_number = Column(u'beta_number', INTEGER())
    build_id = Column(u'build_id', NUMERIC(), primary_key=True, nullable=False)
    # DEPRECATED COLUMN -- vendor supplied data, so this is a channel, not a
    # type, use 'update_channel' instead
    build_type = Column(u'build_type', CITEXT(),
                        primary_key=True, nullable=False)
    platform = Column(u'platform', TEXT(), primary_key=True, nullable=False)
    product_name = Column(u'product_name', CITEXT(),
                          primary_key=True, nullable=False)
    repository = Column(u'repository', CITEXT(), primary_key=True,
                        nullable=False, server_default='mozilla-release')
    version = Column(u'version', TEXT(), primary_key=True, nullable=False)
    update_channel = Column(u'update_channel', TEXT())
    # Above is a transition definition.
    # Ultimately we will define build_type as follows:
    # update_channel = Column(u'update_channel', TEXT(), primary_key=True, nullable=False)
    version_build = Column(u'version_build', TEXT())

    # relationship definitions

    __table_args__ = {}
    # TODO function-based index
    # from sqlalchemy import func
    # Index('releases_raw_date', func.build_date(build_id));


class ReportPartitionInfo(DeclarativeBase):
    __tablename__ = 'report_partition_info'

    # column definitions
    build_order = Column(u'build_order', INTEGER(),
                         nullable=False, server_default=text('1'))
    fkeys = Column(u'fkeys', ARRAY(TEXT()), nullable=False,
                   server_default=text("'{}'::text[]"))
    indexes = Column(u'indexes', ARRAY(TEXT()), nullable=False,
                     server_default=text("'{}'::text[]"))
    keys = Column(u'keys', ARRAY(TEXT()), nullable=False,
                  server_default=text("'{}'::text[]"))
    table_name = Column(u'table_name', CITEXT(),
                        primary_key=True, nullable=False)
    partition_column = Column(u'partition_column', TEXT(), nullable=False)
    timetype = Column(u'timetype', TEXT(), nullable=False)


class ReportsClean(DeclarativeBase):
    __tablename__ = 'reports_clean'

    # column definitions
    address_id = Column(u'address_id', INTEGER(), nullable=False)
    architecture = Column(u'architecture', CITEXT())
    build = Column(u'build', NUMERIC())
    client_crash_date = Column(u'client_crash_date', TIMESTAMP(timezone=True))
    cores = Column(u'cores', INTEGER())
    date_processed = Column(u'date_processed', TIMESTAMP(
        timezone=True), nullable=False)
    domain_id = Column(u'domain_id', INTEGER(), nullable=False)
    duplicate_of = Column(u'duplicate_of', TEXT())
    flash_process_dump = Column(
        u'flash_process_dump', flash_process_dump_type())
    flash_version_id = Column(u'flash_version_id', INTEGER(), nullable=False)
    hang_id = Column(u'hang_id', TEXT())
    install_age = Column(u'install_age', INTERVAL())
    os_name = Column(u'os_name', CITEXT(), nullable=False)
    os_version_id = Column(u'os_version_id', INTEGER(), nullable=False)
    process_type = Column(u'process_type', CITEXT(), nullable=False)
    product_version_id = Column(
        u'product_version_id', INTEGER(), autoincrement=False)
    reason_id = Column(u'reason_id', INTEGER(), nullable=False)
    release_channel = Column(u'release_channel', CITEXT(),
                             nullable=False)  # DEPRECATED
    signature_id = Column(u'signature_id', INTEGER(), nullable=False)
    uptime = Column(u'uptime', INTERVAL())
    uuid = Column(u'uuid', TEXT(), primary_key=True, nullable=False)
    exploitability = Column(u'exploitability', TEXT())
    # New column build_type replaces 'release_channel'
    build_type = Column(u'build_type', build_type())
    # Above is a transition definition.
    # Down the road, this column will be defined as:
    # build_type = Column(u'build_type'), primary_key=True, nullable=False)
    update_channel = Column(u'update_channel', TEXT())


class ReportsDuplicate(DeclarativeBase):
    __tablename__ = 'reports_duplicates'

    # column definitions
    date_processed = Column(u'date_processed', TIMESTAMP(
        timezone=True), nullable=False)
    duplicate_of = Column(u'duplicate_of', TEXT(), nullable=False, index=True)
    uuid = Column(u'uuid', TEXT(), primary_key=True, nullable=False)

    __table_args__ = (
        Index('reports_duplicates_timestamp', date_processed, uuid),
    )


class ReportsUserInfo(DeclarativeBase):
    __tablename__ = 'reports_user_info'

    # column definitions
    app_notes = Column(u'app_notes', CITEXT())
    date_processed = Column(u'date_processed', TIMESTAMP(
        timezone=True), nullable=False)
    email = Column(u'email', CITEXT())
    url = Column(u'url', TEXT())
    user_comments = Column(u'user_comments', CITEXT())
    uuid = Column(u'uuid', TEXT(), primary_key=True, nullable=False)


class Signature(DeclarativeBase):
    __tablename__ = 'signatures'

    # column definitions
    first_build = Column(u'first_build', NUMERIC())
    first_report = Column(u'first_report', TIMESTAMP(timezone=True))
    signature = Column(u'signature', TEXT(), index=True, unique=True)
    signature_id = Column(u'signature_id', INTEGER(),
                          primary_key=True, nullable=False)

    # relationship definitions
    products = relationship(
        'Product',
        primaryjoin='Signature.signature_id==SignatureProductsRollup.signature_id',
        secondary='SignatureProductsRollup',
        secondaryjoin='SignatureProductsRollup.product_name==Product.product_name')


class SignatureProduct(DeclarativeBase):
    __tablename__ = 'signature_products'

    # column definitions
    first_report = Column(u'first_report', TIMESTAMP(timezone=True))
    product_version_id = Column(u'product_version_id', INTEGER(),
                                primary_key=True, nullable=False, autoincrement=False, index=True)
    signature_id = Column(u'signature_id', INTEGER(), ForeignKey(
        'signatures.signature_id'), primary_key=True, nullable=False)

    # relationship definitions
    signatures = relationship(
        'Signature', primaryjoin='SignatureProduct.signature_id==Signature.signature_id')


class SignatureProductsRollup(DeclarativeBase):
    __tablename__ = 'signature_products_rollup'

    signature_id = Column(u'signature_id', INTEGER(), ForeignKey(
        'signatures.signature_id'), primary_key=True, nullable=False)
    product_name = Column(u'product_name', CITEXT(), ForeignKey(
        'products.product_name'), primary_key=True, nullable=False)
    ver_count = Column(u'ver_count', INTEGER(),
                       nullable=False, server_default=text('0'))
    version_list = Column(u'version_list', ARRAY(
        TEXT()), nullable=False, server_default=text("'{}'::text[]"))

    # relationship definitions
    products = relationship(
        'Product', primaryjoin='SignatureProductsRollup.product_name==Product.product_name')
    signatures = relationship(
        'Signature', primaryjoin='SignatureProductsRollup.signature_id==Signature.signature_id')


class GraphicsDevice(DeclarativeBase):
    __tablename__ = 'graphics_device'

    graphics_device_id = Column(
        u'graphics_device_id', INTEGER(), primary_key=True, nullable=False)
    vendor_hex = Column(u'vendor_hex', TEXT())
    adapter_hex = Column(u'adapter_hex', TEXT())
    vendor_name = Column(u'vendor_name', TEXT())
    adapter_name = Column(u'adapter_name', TEXT())


class SpecialProductPlatform(DeclarativeBase):
    """ Currently used for android platform. Uses platform, product name, repo, build_type
        to rename a product_name """
    __tablename__ = 'special_product_platforms'

    # column definitions
    min_version = Column(u'min_version', MAJOR_VERSION())
    platform = Column(u'platform', CITEXT(), primary_key=True, nullable=False)
    product_name = Column(u'product_name', CITEXT(), nullable=False)
    release_channel = Column(u'release_channel', CITEXT(
    ), primary_key=True, nullable=False)  # DEPRECATED
    release_name = Column(u'release_name', CITEXT(),
                          primary_key=True, nullable=False)  # DEPRECATED
    repository = Column(u'repository', CITEXT(),
                        primary_key=True, nullable=False)
    build_type = Column(u'build_type', build_type())
    # Above is a transition definition.
    # Ultimately we will define build_type as follows:
    # build_type = Column(u'build_type', build_type(), primary_key=True, nullable=False)


class Crontabber(DeclarativeBase):
    __tablename__ = 'crontabber'

    # column definitions
    app_name = Column(u'app_name', TEXT(), primary_key=True, nullable=False)
    next_run = Column(u'next_run', TIMESTAMP(timezone=True))
    first_run = Column(u'first_run', TIMESTAMP(timezone=True))
    last_run = Column(u'last_run', TIMESTAMP(timezone=True))
    last_success = Column(u'last_success', TIMESTAMP(timezone=True))
    error_count = Column(u'error_count', INTEGER(), server_default=text('0'))
    depends_on = Column(u'depends_on', ARRAY(TEXT()))
    last_error = Column(u'last_error', JSON())
    ongoing = Column(u'ongoing', TIMESTAMP(timezone=True))

    __table_args__ = (
        Index('crontabber_app_name_idx', app_name, unique=True),
    )


class CrontabberLog(DeclarativeBase):
    __tablename__ = 'crontabber_log'

    # column definitions
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    app_name = Column(u'app_name', TEXT(), nullable=False)
    log_time = Column(u'log_time', TIMESTAMP(timezone=True), nullable=False,
                      server_default=text('NOW()'))
    duration = Column(u'duration', INTERVAL())
    success = Column(u'success', TIMESTAMP(timezone=True))
    exc_type = Column(u'exc_type', TEXT())
    exc_value = Column(u'exc_value', TEXT())
    exc_traceback = Column(u'exc_traceback', TEXT())

    __table_args__ = (
        Index('crontabber_log_app_name_idx', app_name),
        Index('crontabber_log_log_time_idx', log_time),
    )


class RawUpdateChannel(DeclarativeBase):
    """ Scraped information from reports table for release_channel/update_channel """
    __tablename__ = 'raw_update_channels'

    update_channel = Column(u'update_channel', CITEXT(),
                            nullable=False, primary_key=True)
    product_name = Column(u'product_name', TEXT(),
                          nullable=False, primary_key=True)
    version = Column(u'version', TEXT(), nullable=False, primary_key=True)
    build = Column(u'build', NUMERIC(), nullable=False, primary_key=True)
    first_report = Column(u'first_report', TIMESTAMP(
        timezone=True), nullable=False)


class UpdateChannelMap(DeclarativeBase):
    """ Human-defined mapping from raw_update_channel to new update_channel
    name for reports_clean """
    __tablename__ = 'update_channel_map'

    update_channel = Column(u'update_channel', CITEXT(),
                            nullable=False, primary_key=True)
    productid = Column(u'productid', TEXT(), nullable=False, primary_key=True)
    version_field = Column(u'version_field', TEXT(),
                           nullable=False, primary_key=True)
    rewrite = Column(u'rewrite', JSON(), nullable=False)


class Correlations(DeclarativeBase):
    __tablename__ = 'correlations'

    # column definitions
    id = Column(u'id', INTEGER(), primary_key=True,
                autoincrement=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(
    ), nullable=False, autoincrement=False, index=True)
    platform = Column(u'platform', TEXT(), primary_key=True, nullable=False)
    signature_id = Column(u'signature_id', INTEGER(),
                          primary_key=False, nullable=False, index=True)
    key = Column(u'key', TEXT(), nullable=False)
    count = Column(u'count', INTEGER(), nullable=False,
                   server_default=text('0'))
    notes = Column(u'notes', TEXT(), primary_key=False,
                   nullable=False, server_default='')
    date = Column(u'date', DATE(), primary_key=False,
                  nullable=False, index=True)
    payload = Column(u'payload', JSON())

    # When looking for signatures by the correlations you need to query by:
    #  product_version_id
    #  platform
    #  date
    #  key
    #
    # When looking for correlations for a specific signature you need:
    #  product_version_id
    #  platform
    #  key
    #  date
    #  signature
    #
    __table_args__ = (
        Index(
            'correlations_signatures_idx',
            product_version_id,
            platform,
            key,
            date,
        ),
        Index(
            'correlations_signature_idx',
            product_version_id,
            platform,
            key,
            date,
            signature_id,
            unique=True
        ),
    )

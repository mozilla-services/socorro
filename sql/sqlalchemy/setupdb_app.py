#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


"""
Create, prepare and load schema for Socorro PostgreSQL database.
"""
from __future__ import unicode_literals

import sys
import psycopg2
import psycopg2.extensions
from psycopg2 import ProgrammingError
import re
import logging

from socorro.app.generic_app import App, main
from configman import Namespace

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import sqlalchemy.types as types
try:
    from sqlalchemy.dialects.postgresql import *
except ImportError:
    from sqlalchemy.databases.postgres import *

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata

# Create CITEXT type
class CITEXT(types.UserDefinedType):

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
# End citext type

# Schema definition
email_campaigns_contacts = Table(u'email_campaigns_contacts', metadata,
    Column(u'email_campaigns_id', INTEGER(), ForeignKey('email_campaigns.id')),
    Column(u'email_contacts_id', INTEGER(), ForeignKey('email_contacts.id')),
    Column(u'status', TEXT(), nullable=False, default='stopped'),
)

product_release_channels = Table(u'product_release_channels', metadata,
    Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), primary_key=True, nullable=False),
    Column(u'release_channel', CITEXT(), ForeignKey('release_channels.release_channel'), primary_key=True, nullable=False),
    Column(u'throttle', NUMERIC(), nullable=False, default=float(1.0)),
)

product_versions = Table(u'product_versions', metadata,
    Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False),
    Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), nullable=False),
    Column(u'major_version', TEXT()),
    Column(u'release_version', CITEXT(), nullable=False),
    Column(u'version_string', CITEXT(), nullable=False),
    Column(u'beta_number', INTEGER()),
    Column(u'version_sort', TEXT(), nullable=False, default=0),
    Column(u'build_date', DATE(), nullable=False),
    Column(u'sunset_date', DATE(), nullable=False),
    Column(u'featured_version', BOOLEAN(), nullable=False, default=False),
    Column(u'build_type', CITEXT(), nullable=False, default='release'),
    Column(u'has_builds', BOOLEAN()),
    Column(u'is_rapid_beta', BOOLEAN(), default=False),
    Column(u'rapid_beta_id', INTEGER(), ForeignKey('product_versions.product_version_id')),
)

signature_products_rollup = Table(u'signature_products_rollup', metadata,
    Column(u'signature_id', INTEGER(), ForeignKey('signatures.signature_id'), primary_key=True, nullable=False),
    Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), primary_key=True, nullable=False),
    Column(u'ver_count', INTEGER(), nullable=False, default=0),
    Column(u'version_list', ARRAY(TEXT()), nullable=False, server_default=text("'{}'::text[]")),
)

tcbses = Table(u'tcbs', metadata,
    Column(u'signature_id', INTEGER(), ForeignKey('signatures.signature_id'), primary_key=True, nullable=False),
    Column(u'report_date', DATE(), primary_key=True, nullable=False),
    Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False),
    Column(u'process_type', CITEXT(), primary_key=True, nullable=False),
    Column(u'release_channel', CITEXT(), ForeignKey('release_channels.release_channel'), primary_key=True, nullable=False),
    Column(u'report_count', INTEGER(), nullable=False, default=0),
    Column(u'win_count', INTEGER(), nullable=False, default=0),
    Column(u'mac_count', INTEGER(), nullable=False, default=0),
    Column(u'lin_count', INTEGER(), nullable=False, default=0),
    Column(u'hang_count', INTEGER(), nullable=False, default=0),
    Column(u'startup_count', INTEGER()),
)

correlation_addons = Table(u'correlation_addons', metadata,
    Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False),
    Column(u'addon_key', TEXT(), nullable=False),
    Column(u'addon_version', TEXT(), nullable=False),
    Column(u'crash_count', INTEGER(), nullable=False, default='0'),
)

correlation_cores = Table(u'correlation_cores', metadata,
    Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False),
    Column(u'architecture', CITEXT(), nullable=False),
    Column(u'cores', INTEGER(), nullable=False),
    Column(u'crash_count', INTEGER(), nullable=False, default='0'),
)

correlation_modules = Table(u'correlation_modules', metadata,
    Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False),
    Column(u'module_signature', TEXT(), nullable=False),
    Column(u'module_version', TEXT(), nullable=False),
    Column(u'crash_count', INTEGER(), nullable=False, default='0'),
)

extensions = Table(u'extensions', metadata,
    Column(u'report_id', INTEGER(), nullable=False),
    Column(u'date_processed', TIMESTAMP(timezone=True)),
    Column(u'extension_key', INTEGER(), nullable=False),
    Column(u'extension_id', TEXT(), nullable=False),
    Column(u'extension_version', TEXT()),
)

plugins_reports = Table(u'plugins_reports', metadata,
    Column(u'report_id', INTEGER(), nullable=False),
    Column(u'plugin_id', INTEGER(), nullable=False),
    Column(u'date_processed', TIMESTAMP(timezone=True)),
    Column(u'version', TEXT(), nullable=False),
)

priorityjobs_log = Table(u'priorityjobs_log', metadata,
    Column(u'uuid', VARCHAR(length=255)),
)

raw_adu = Table(u'raw_adu', metadata,
    Column(u'adu_count', INTEGER()),
    Column(u'date', DATE()),
    Column(u'product_name', TEXT()),
    Column(u'product_os_platform', TEXT()),
    Column(u'product_os_version', TEXT()),
    Column(u'product_version', TEXT()),
    Column(u'build', TEXT()),
    Column(u'build_channel', TEXT()),
    Column(u'product_guid', TEXT()),
)

replication_test = Table(u'replication_test', metadata,
    Column(u'id', SMALLINT()),
    Column(u'test', BOOLEAN()),
)

reports = Table(u'reports', metadata,
    Column(u'id', INTEGER(), nullable=False),
    Column(u'client_crash_date', TIMESTAMP(timezone=True)),
    Column(u'date_processed', TIMESTAMP(timezone=True)),
    Column(u'uuid', VARCHAR(length=50), nullable=False),
    Column(u'product', VARCHAR(length=30)),
    Column(u'version', VARCHAR(length=16)),
    Column(u'build', VARCHAR(length=30)),
    Column(u'signature', VARCHAR(length=255)),
    Column(u'url', VARCHAR(length=255)),
    Column(u'install_age', INTEGER()),
    Column(u'last_crash', INTEGER()),
    Column(u'uptime', INTEGER()),
    Column(u'cpu_name', VARCHAR(length=100)),
    Column(u'cpu_info', VARCHAR(length=100)),
    Column(u'reason', VARCHAR(length=255)),
    Column(u'address', VARCHAR(length=20)),
    Column(u'os_name', VARCHAR(length=100)),
    Column(u'os_version', VARCHAR(length=100)),
    Column(u'email', VARCHAR(length=100)),
    Column(u'user_id', VARCHAR(length=50)),
    Column(u'started_datetime', TIMESTAMP(timezone=True)),
    Column(u'completed_datetime', TIMESTAMP(timezone=True)),
    Column(u'success', BOOLEAN()),
    Column(u'truncated', BOOLEAN()),
    Column(u'processor_notes', TEXT()),
    Column(u'user_comments', VARCHAR(length=1024)),
    Column(u'app_notes', VARCHAR(length=1024)),
    Column(u'distributor', VARCHAR(length=20)),
    Column(u'distributor_version', VARCHAR(length=20)),
    Column(u'topmost_filenames', TEXT()),
    Column(u'addons_checked', BOOLEAN()),
    Column(u'flash_version', TEXT()),
    Column(u'hangid', TEXT()),
    Column(u'process_type', TEXT()),
    Column(u'release_channel', TEXT()),
    Column(u'productid', TEXT()),
)

reports_bad = Table(u'reports_bad', metadata,
    Column(u'uuid', TEXT(), nullable=False),
    Column(u'date_processed', TIMESTAMP(timezone=True), nullable=False),
)

windows_versions = Table(u'windows_versions', metadata,
    Column(u'windows_version_name', CITEXT(), nullable=False),
    Column(u'major_version', INTEGER(), nullable=False),
    Column(u'minor_version', INTEGER(), nullable=False),
)

class Address(DeclarativeBase):
    __tablename__ = 'addresses'

    __table_args__ = {}

    #column definitions
    address = Column(u'address', CITEXT(), nullable=False)
    address_id = Column(u'address_id', INTEGER(), primary_key=True, nullable=False)
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))

    #relationship definitions


class Bug(DeclarativeBase):
    __tablename__ = 'bugs'

    __table_args__ = {}

    #column definitions
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    resolution = Column(u'resolution', TEXT())
    short_desc = Column(u'short_desc', TEXT())
    status = Column(u'status', TEXT())

    #relationship definitions


class BugAssociation(DeclarativeBase):
    __tablename__ = 'bug_associations'

    __table_args__ = {}

    #column definitions
    bug_id = Column(u'bug_id', INTEGER(), ForeignKey('bugs.id'), primary_key=True, nullable=False)
    signature = Column(u'signature', TEXT(), primary_key=True, nullable=False)

    #relationship definitions
    bugs = relationship('Bug', primaryjoin='BugAssociation.bug_id==Bug.id')


class BuildAdu(DeclarativeBase):
    __tablename__ = 'build_adu'

    __table_args__ = {}

    #column definitions
    adu_count = Column(u'adu_count', INTEGER(), nullable=False)
    adu_date = Column(u'adu_date', DATE(), primary_key=True, nullable=False)
    build_date = Column(u'build_date', DATE(), primary_key=True, nullable=False)
    os_name = Column(u'os_name', CITEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)

    #relationship definitions


class Correlations(DeclarativeBase):
    __tablename__ = 'correlations'

    __table_args__ = {}

    #column definitions
    correlation_id = Column(u'correlation_id', INTEGER(), primary_key=True, nullable=False)
    crash_count = Column(u'crash_count', INTEGER(), nullable=False, default=0)
    os_name = Column(u'os_name', CITEXT(), nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), nullable=False)
    reason_id = Column(u'reason_id', INTEGER(), nullable=False)
    signature_id = Column(u'signature_id', INTEGER(), nullable=False)

    #relationship definitions


class CrashType(DeclarativeBase):
    __tablename__ = 'crash_types'

    __table_args__ = {}

    #column definitions
    crash_type = Column(u'crash_type', CITEXT(), nullable=False)
    crash_type_id = Column(u'crash_type_id', INTEGER(), primary_key=True, nullable=False)
    crash_type_short = Column(u'crash_type_short', CITEXT(), nullable=False)
    has_hang_id = Column(u'has_hang_id', BOOLEAN())
    include_agg = Column(u'include_agg', BOOLEAN(), nullable=False, default=True)
    old_code = Column(u'old_code', CHAR(length=1), nullable=False)
    process_type = Column(u'process_type', CITEXT(), ForeignKey('process_types.process_type'), nullable=False)

    #relationship definitions
    process_types = relationship('ProcessType', primaryjoin='CrashType.process_type==ProcessType.process_type')


class CrashesByUser(DeclarativeBase):
    __tablename__ = 'crashes_by_user'

    __table_args__ = {}

    #column definitions
    adu = Column(u'adu', INTEGER(), nullable=False)
    crash_type_id = Column(u'crash_type_id', INTEGER(), ForeignKey('crash_types.crash_type_id'), primary_key=True, nullable=False)
    os_short_name = Column(u'os_short_name', CITEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False)
    report_date = Column(u'report_date', DATE(), primary_key=True, nullable=False)

    #relationship definitions
    crash_types = relationship('CrashType', primaryjoin='CrashesByUser.crash_type_id==CrashType.crash_type_id')


class CrashesByUserBuild(DeclarativeBase):
    __tablename__ = 'crashes_by_user_build'

    __table_args__ = {}

    #column definitions
    adu = Column(u'adu', INTEGER(), nullable=False)
    build_date = Column(u'build_date', DATE(), primary_key=True, nullable=False)
    crash_type_id = Column(u'crash_type_id', INTEGER(), ForeignKey('crash_types.crash_type_id'), primary_key=True, nullable=False)
    os_short_name = Column(u'os_short_name', CITEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False)
    report_date = Column(u'report_date', DATE(), primary_key=True, nullable=False)

    #relationship definitions
    crash_types = relationship('CrashType', primaryjoin='CrashesByUserBuild.crash_type_id==CrashType.crash_type_id')


class CrontabberState(DeclarativeBase):
    __tablename__ = 'crontabber_state'

    __table_args__ = {}

    #column definitions
    last_updated = Column(u'last_updated', TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    state = Column(u'state', TEXT(), nullable=False)

    #relationship definitions


class DailyHang(DeclarativeBase):
    __tablename__ = 'daily_hangs'

    __table_args__ = {}

    #column definitions
    browser_signature_id = Column(u'browser_signature_id', INTEGER(), nullable=False)
    duplicates = Column(u'duplicates', ARRAY(TEXT()))
    flash_version_id = Column(u'flash_version_id', INTEGER())
    hang_id = Column(u'hang_id', TEXT(), nullable=False)
    plugin_signature_id = Column(u'plugin_signature_id', INTEGER(), nullable=False)
    plugin_uuid = Column(u'plugin_uuid', TEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), nullable=False)
    report_date = Column(u'report_date', DATE())
    url = Column(u'url', CITEXT())
    uuid = Column(u'uuid', TEXT(), nullable=False)

    #relationship definitions


class Domain(DeclarativeBase):
    __tablename__ = 'domains'

    __table_args__ = {}

    #column definitions
    domain = Column(u'domain', CITEXT(), nullable=False)
    domain_id = Column(u'domain_id', INTEGER(), primary_key=True, nullable=False)
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))

    #relationship definitions


class EmailCampaign(DeclarativeBase):
    __tablename__ = 'email_campaigns'

    __table_args__ = {}

    #column definitions
    author = Column(u'author', TEXT(), nullable=False)
    body = Column(u'body', TEXT(), nullable=False)
    date_created = Column(u'date_created', TIMESTAMP(timezone=True), nullable=False, default=text('NOW()'))
    email_count = Column(u'email_count', INTEGER(), default=0)
    end_date = Column(u'end_date', TIMESTAMP(timezone=True), nullable=False)
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    product = Column(u'product', TEXT(), nullable=False)
    signature = Column(u'signature', TEXT(), nullable=False)
    start_date = Column(u'start_date', TIMESTAMP(timezone=True), nullable=False)
    status = Column(u'status', TEXT(), nullable=False, default='stopped')
    subject = Column(u'subject', TEXT(), nullable=False)
    versions = Column(u'versions', TEXT(), nullable=False)

    #relationship definitions
    email_contacts = relationship('EmailContact', primaryjoin='EmailCampaign.id==email_campaigns_contacts.c.email_campaigns_id', secondary=email_campaigns_contacts, secondaryjoin='email_campaigns_contacts.c.email_contacts_id==EmailContact.id')


class EmailContact(DeclarativeBase):
    __tablename__ = 'email_contacts'

    __table_args__ = {}

    #column definitions
    crash_date = Column(u'crash_date', TIMESTAMP(timezone=True))
    email = Column(u'email', TEXT(), nullable=False)
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    ooid = Column(u'ooid', TEXT())
    subscribe_status = Column(u'subscribe_status', BOOLEAN(), default=True)
    subscribe_token = Column(u'subscribe_token', TEXT(), nullable=False)

    #relationship definitions
    email_campaigns = relationship('EmailCampaign', primaryjoin='EmailContact.id==email_campaigns_contacts.c.email_contacts_id', secondary=email_campaigns_contacts, secondaryjoin='email_campaigns_contacts.c.email_campaigns_id==EmailCampaign.id')


class Explosivenes(DeclarativeBase):
    __tablename__ = 'explosiveness'

    __table_args__ = {}

    #column definitions
    day0 = Column(u'day0', NUMERIC())
    day1 = Column(u'day1', NUMERIC())
    day2 = Column(u'day2', NUMERIC())
    day3 = Column(u'day3', NUMERIC())
    day4 = Column(u'day4', NUMERIC())
    day5 = Column(u'day5', NUMERIC())
    day6 = Column(u'day6', NUMERIC())
    day7 = Column(u'day7', NUMERIC())
    day8 = Column(u'day8', NUMERIC())
    day9 = Column(u'day9', NUMERIC())
    last_date = Column(u'last_date', DATE(), primary_key=True, nullable=False)
    oneday = Column(u'oneday', NUMERIC())
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    signature_id = Column(u'signature_id', INTEGER(), primary_key=True, nullable=False)
    threeday = Column(u'threeday', NUMERIC())

    #relationship definitions


class FlashVersion(DeclarativeBase):
    __tablename__ = 'flash_versions'

    __table_args__ = {}

    #column definitions
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))
    flash_version = Column(u'flash_version', CITEXT(), nullable=False)
    flash_version_id = Column(u'flash_version_id', INTEGER(), primary_key=True, nullable=False)

    #relationship definitions


class HomePageGraph(DeclarativeBase):
    __tablename__ = 'home_page_graph'

    __table_args__ = {}

    #column definitions
    adu = Column(u'adu', INTEGER(), nullable=False, default=0)
    crash_hadu = Column(u'crash_hadu', NUMERIC(), nullable=False, default=float(0.0))
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, default=0)
    report_date = Column(u'report_date', DATE(), primary_key=True, nullable=False)

    #relationship definitions


class HomePageGraphBuild(DeclarativeBase):
    __tablename__ = 'home_page_graph_build'

    __table_args__ = {}

    #column definitions
    adu = Column(u'adu', INTEGER(), nullable=False, default=0)
    build_date = Column(u'build_date', DATE(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, default=0)
    report_date = Column(u'report_date', DATE(), primary_key=True, nullable=False)

    #relationship definitions


class Job(DeclarativeBase):
    __tablename__ = 'jobs'

    __table_args__ = {}

    #column definitions
    completeddatetime = Column(u'completeddatetime', TIMESTAMP(timezone=True))
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    message = Column(u'message', TEXT())
    owner = Column(u'owner', INTEGER(), ForeignKey('processors.id'))
    pathname = Column(u'pathname', VARCHAR(length=1024), nullable=False)
    priority = Column(u'priority', INTEGER(), default=0)
    queueddatetime = Column(u'queueddatetime', TIMESTAMP(timezone=True))
    starteddatetime = Column(u'starteddatetime', TIMESTAMP(timezone=True))
    success = Column(u'success', BOOLEAN())
    uuid = Column(u'uuid', VARCHAR(length=50), nullable=False)

    #relationship definitions
    processors = relationship('Processor', primaryjoin='Job.owner==Processor.id')


class NightlyBuild(DeclarativeBase):
    __tablename__ = 'nightly_builds'

    __table_args__ = {}

    #column definitions
    build_date = Column(u'build_date', DATE(), primary_key=True, nullable=False)
    days_out = Column(u'days_out', INTEGER(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, default=0)
    report_date = Column(u'report_date', DATE(), nullable=False)

    #relationship definitions


class OsName(DeclarativeBase):
    __tablename__ = 'os_names'

    __table_args__ = {}

    #column definitions
    os_name = Column(u'os_name', CITEXT(), primary_key=True, nullable=False)
    os_short_name = Column(u'os_short_name', CITEXT(), nullable=False)

    #relationship definitions


class OsNameMatche(DeclarativeBase):
    __tablename__ = 'os_name_matches'

    __table_args__ = {}

    #column definitions
    match_string = Column(u'match_string', TEXT(), primary_key=True, nullable=False)
    os_name = Column(u'os_name', CITEXT(), ForeignKey('os_names.os_name'), primary_key=True, nullable=False)

    #relationship definitions
    os_names = relationship('OsName', primaryjoin='OsNameMatche.os_name==OsName.os_name')


class OsVersion(DeclarativeBase):
    __tablename__ = 'os_versions'

    __table_args__ = {}

    #column definitions
    major_version = Column(u'major_version', INTEGER(), nullable=False)
    minor_version = Column(u'minor_version', INTEGER(), nullable=False)
    os_name = Column(u'os_name', CITEXT(), ForeignKey('os_names.os_name'), nullable=False)
    os_version_id = Column(u'os_version_id', INTEGER(), primary_key=True, nullable=False)
    os_version_string = Column(u'os_version_string', CITEXT())

    #relationship definitions
    os_names = relationship('OsName', primaryjoin='OsVersion.os_name==OsName.os_name')


class Plugin(DeclarativeBase):
    __tablename__ = 'plugins'

    __table_args__ = {}

    #column definitions
    filename = Column(u'filename', TEXT(), nullable=False)
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    name = Column(u'name', TEXT(), nullable=False)

    #relationship definitions


class Priorityjob(DeclarativeBase):
    __tablename__ = 'priorityjobs'

    __table_args__ = {}

    #column definitions
    uuid = Column(u'uuid', VARCHAR(length=255), primary_key=True, nullable=False)

    #relationship definitions


class PriorityjobsLoggingSwitch(DeclarativeBase):
    __tablename__ = 'priorityjobs_logging_switch'

    __table_args__ = {}

    #column definitions
    log_jobs = Column(u'log_jobs', BOOLEAN(), primary_key=True, nullable=False)

    #relationship definitions


class ProcessType(DeclarativeBase):
    __tablename__ = 'process_types'

    __table_args__ = {}

    #column definitions
    process_type = Column(u'process_type', CITEXT(), primary_key=True, nullable=False)

    #relationship definitions


class Processor(DeclarativeBase):
    __tablename__ = 'processors'

    __table_args__ = {}

    #column definitions
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    lastseendatetime = Column(u'lastseendatetime', TIMESTAMP())
    name = Column(u'name', VARCHAR(length=255), nullable=False)
    startdatetime = Column(u'startdatetime', TIMESTAMP(), nullable=False)

    #relationship definitions


class Product(DeclarativeBase):
    __tablename__ = 'products'

    __table_args__ = {}

    #column definitions
    product_name = Column(u'product_name', CITEXT(), primary_key=True, nullable=False)
    rapid_beta_version = Column(u'rapid_beta_version', TEXT())
    rapid_release_version = Column(u'rapid_release_version', TEXT())
    release_name = Column(u'release_name', CITEXT(), nullable=False)
    sort = Column(u'sort', SMALLINT(), nullable=False, default=0)

    #relationship definitions
    release_channels = relationship('ReleaseChannel', primaryjoin='Product.product_name==ProductReleaseChannel.product_name', secondary=product_release_channels, secondaryjoin='ProductReleaseChannel.release_channel==ReleaseChannel.release_channel')
    product_versions = relationship('ProductVersion', primaryjoin='Product.product_name==ProductVersion.product_name', secondary=product_versions, secondaryjoin='ProductVersion.rapid_beta_id==ProductVersion.product_version_id')
    signatures = relationship('Signature', primaryjoin='Product.product_name==SignatureProductsRollup.product_name', secondary=signature_products_rollup, secondaryjoin='SignatureProductsRollup.signature_id==Signature.signature_id')


class ProductAdu(DeclarativeBase):
    __tablename__ = 'product_adu'

    __table_args__ = {}

    #column definitions
    adu_count = Column(u'adu_count', BIGINT(), nullable=False, default=0)
    adu_date = Column(u'adu_date', DATE(), primary_key=True, nullable=False)
    os_name = Column(u'os_name', CITEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)

    #relationship definitions


class ProductProductidMap(DeclarativeBase):
    __tablename__ = 'product_productid_map'

    __table_args__ = {}

    #column definitions
    product_name = Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), nullable=False)
    productid = Column(u'productid', TEXT(), primary_key=True, nullable=False)
    rewrite = Column(u'rewrite', BOOLEAN(), nullable=False, default=False)
    version_began = Column(u'version_began', TEXT())
    version_ended = Column(u'version_ended', TEXT())

    #relationship definitions
    products = relationship('Product', primaryjoin='ProductProductidMap.product_name==Product.product_name')


class ProductReleaseChannel(DeclarativeBase):
    __table__ = product_release_channels

    #relationship definitions
    release_channels = relationship('ReleaseChannel', primaryjoin='ProductReleaseChannel.release_channel==ReleaseChannel.release_channel')
    products = relationship('Product', primaryjoin='ProductReleaseChannel.product_name==Product.product_name')


class ProductVersion(DeclarativeBase):
    __table__ = product_versions


    #relationship definitions
    products = relationship('Product', primaryjoin='ProductVersion.product_version_id==ProductVersion.rapid_beta_id', secondary=product_versions, secondaryjoin='ProductVersion.product_name==Product.product_name')
    product_versions = relationship('ProductVersion', primaryjoin='ProductVersion.rapid_beta_id==ProductVersion.product_version_id')


class ProductVersionBuild(DeclarativeBase):
    __tablename__ = 'product_version_builds'

    __table_args__ = {}

    #column definitions
    build_id = Column(u'build_id', NUMERIC(), primary_key=True, nullable=False)
    platform = Column(u'platform', TEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), ForeignKey('product_versions.product_version_id'), primary_key=True, nullable=False)
    repository = Column(u'repository', CITEXT())

    #relationship definitions
    product_versions = relationship('ProductVersion', primaryjoin='ProductVersionBuild.product_version_id==ProductVersion.product_version_id')


class RankCompare(DeclarativeBase):
    __tablename__ = 'rank_compare'

    __table_args__ = {}

    #column definitions
    percent_of_total = Column(u'percent_of_total', NUMERIC())
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    rank_days = Column(u'rank_days', INTEGER(), primary_key=True, nullable=False)
    rank_report_count = Column(u'rank_report_count', INTEGER())
    report_count = Column(u'report_count', INTEGER())
    signature_id = Column(u'signature_id', INTEGER(), primary_key=True, nullable=False)
    total_reports = Column(u'total_reports', BIGINT())

    #relationship definitions


class Reason(DeclarativeBase):
    __tablename__ = 'reasons'

    __table_args__ = {}

    #column definitions
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))
    reason = Column(u'reason', CITEXT(), nullable=False)
    reason_id = Column(u'reason_id', INTEGER(), primary_key=True, nullable=False)

    #relationship definitions


class ReleaseChannel(DeclarativeBase):
    __tablename__ = 'release_channels'

    __table_args__ = {}

    #column definitions
    release_channel = Column(u'release_channel', CITEXT(), primary_key=True, nullable=False)
    sort = Column(u'sort', SMALLINT(), nullable=False, default=0)

    #relationship definitions
    products = relationship('Product', primaryjoin='ReleaseChannel.release_channel==ProductReleaseChannel.release_channel', secondary=product_release_channels, secondaryjoin='ProductReleaseChannel.product_name==Product.product_name')
    signatures = relationship('Signature', primaryjoin='ReleaseChannel.release_channel==Tcbs.release_channel', secondary=tcbses, secondaryjoin='Tcbs.signature_id==Signature.signature_id')


class ReleaseChannelMatche(DeclarativeBase):
    __tablename__ = 'release_channel_matches'

    __table_args__ = {}

    #column definitions
    match_string = Column(u'match_string', TEXT(), primary_key=True, nullable=False)
    release_channel = Column(u'release_channel', CITEXT(), ForeignKey('release_channels.release_channel'), primary_key=True, nullable=False)

    #relationship definitions
    release_channels = relationship('ReleaseChannel', primaryjoin='ReleaseChannelMatche.release_channel==ReleaseChannel.release_channel')


class ReleaseRepository(DeclarativeBase):
    __tablename__ = 'release_repositories'

    __table_args__ = {}

    #column definitions
    repository = Column(u'repository', CITEXT(), primary_key=True, nullable=False)

    #relationship definitions


class ReleasesRaw(DeclarativeBase):
    __tablename__ = 'releases_raw'

    __table_args__ = {}

    #column definitions
    beta_number = Column(u'beta_number', INTEGER())
    build_id = Column(u'build_id', NUMERIC(), primary_key=True, nullable=False)
    build_type = Column(u'build_type', CITEXT(), primary_key=True, nullable=False)
    platform = Column(u'platform', TEXT(), primary_key=True, nullable=False)
    product_name = Column(u'product_name', CITEXT(), primary_key=True, nullable=False)
    repository = Column(u'repository', CITEXT(), primary_key=True, nullable=False, default='mozilla-release')
    version = Column(u'version', TEXT(), primary_key=True, nullable=False)

    #relationship definitions


class ReportPartitionInfo(DeclarativeBase):
    __tablename__ = 'report_partition_info'

    __table_args__ = {}

    #column definitions
    build_order = Column(u'build_order', INTEGER(), nullable=False, default=1)
    fkeys = Column(u'fkeys', ARRAY(TEXT()), nullable=False, server_default=text("'{}'::text[]"))
    indexes = Column(u'indexes', ARRAY(TEXT()), nullable=False, server_default=text("'{}'::text[]"))
    keys = Column(u'keys', ARRAY(TEXT()), nullable=False, server_default=text("'{}'::text[]"))
    table_name = Column(u'table_name', CITEXT(), primary_key=True, nullable=False)

    #relationship definitions


class ReportsClean(DeclarativeBase):
    __tablename__ = 'reports_clean'

    __table_args__ = {}

    #column definitions
    address_id = Column(u'address_id', INTEGER(), nullable=False)
    architecture = Column(u'architecture', CITEXT())
    build = Column(u'build', NUMERIC())
    client_crash_date = Column(u'client_crash_date', TIMESTAMP(timezone=True))
    cores = Column(u'cores', INTEGER())
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True), nullable=False)
    domain_id = Column(u'domain_id', INTEGER(), nullable=False)
    duplicate_of = Column(u'duplicate_of', TEXT())
    flash_version_id = Column(u'flash_version_id', INTEGER(), nullable=False)
    hang_id = Column(u'hang_id', TEXT())
    install_age = Column(u'install_age', INTERVAL())
    os_name = Column(u'os_name', CITEXT(), nullable=False)
    os_version_id = Column(u'os_version_id', INTEGER(), nullable=False)
    process_type = Column(u'process_type', CITEXT(), nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER())
    reason_id = Column(u'reason_id', INTEGER(), nullable=False)
    release_channel = Column(u'release_channel', CITEXT(), nullable=False)
    signature_id = Column(u'signature_id', INTEGER(), nullable=False)
    uptime = Column(u'uptime', INTERVAL())
    uuid = Column(u'uuid', TEXT(), primary_key=True, nullable=False)

    #relationship definitions


class ReportsDuplicate(DeclarativeBase):
    __tablename__ = 'reports_duplicates'

    __table_args__ = {}

    #column definitions
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True), nullable=False)
    duplicate_of = Column(u'duplicate_of', TEXT(), nullable=False)
    uuid = Column(u'uuid', TEXT(), primary_key=True, nullable=False)

    #relationship definitions


class ReportsUserInfo(DeclarativeBase):
    __tablename__ = 'reports_user_info'

    __table_args__ = {}

    #column definitions
    app_notes = Column(u'app_notes', CITEXT())
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True), nullable=False)
    email = Column(u'email', CITEXT())
    url = Column(u'url', TEXT())
    user_comments = Column(u'user_comments', CITEXT())
    uuid = Column(u'uuid', TEXT(), primary_key=True, nullable=False)

    #relationship definitions


class ServerStatu(DeclarativeBase):
    __tablename__ = 'server_status'

    __table_args__ = {}

    #column definitions
    avg_process_sec = Column(u'avg_process_sec', REAL())
    avg_wait_sec = Column(u'avg_wait_sec', REAL())
    date_created = Column(u'date_created', TIMESTAMP(timezone=True), nullable=False)
    date_oldest_job_queued = Column(u'date_oldest_job_queued', TIMESTAMP(timezone=True))
    date_recently_completed = Column(u'date_recently_completed', TIMESTAMP(timezone=True))
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    processors_count = Column(u'processors_count', INTEGER(), nullable=False)
    waiting_job_count = Column(u'waiting_job_count', INTEGER(), nullable=False)

    #relationship definitions


class Session(DeclarativeBase):
    __tablename__ = 'sessions'

    __table_args__ = {}

    #column definitions
    data = Column(u'data', TEXT(), nullable=False)
    last_activity = Column(u'last_activity', INTEGER(), nullable=False)
    session_id = Column(u'session_id', VARCHAR(length=127), primary_key=True, nullable=False)

    #relationship definitions


class Signature(DeclarativeBase):
    __tablename__ = 'signatures'

    __table_args__ = {}

    #column definitions
    first_build = Column(u'first_build', NUMERIC())
    first_report = Column(u'first_report', TIMESTAMP(timezone=True))
    signature = Column(u'signature', TEXT())
    signature_id = Column(u'signature_id', INTEGER(), primary_key=True, nullable=False)

    #relationship definitions
    products = relationship('Product', primaryjoin='Signature.signature_id==SignatureProductsRollup.signature_id', secondary=signature_products_rollup, secondaryjoin='SignatureProductsRollup.product_name==Product.product_name')
    release_channels = relationship('ReleaseChannel', primaryjoin='Signature.signature_id==Tcbs.signature_id', secondary=tcbses, secondaryjoin='Tcbs.release_channel==ReleaseChannel.release_channel')


class SignatureProduct(DeclarativeBase):
    __tablename__ = 'signature_products'

    __table_args__ = {}

    #column definitions
    first_report = Column(u'first_report', TIMESTAMP(timezone=True))
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    signature_id = Column(u'signature_id', INTEGER(), ForeignKey('signatures.signature_id'), primary_key=True, nullable=False)

    #relationship definitions
    signatures = relationship('Signature', primaryjoin='SignatureProduct.signature_id==Signature.signature_id')


class SignatureProductsRollup(DeclarativeBase):
    __table__ = signature_products_rollup


    #relationship definitions
    products = relationship('Product', primaryjoin='SignatureProductsRollup.product_name==Product.product_name')
    signatures = relationship('Signature', primaryjoin='SignatureProductsRollup.signature_id==Signature.signature_id')


class SocorroDbVersion(DeclarativeBase):
    __tablename__ = 'socorro_db_version'

    __table_args__ = {}

    #column definitions
    current_version = Column(u'current_version', TEXT(), primary_key=True, nullable=False)
    refreshed_at = Column(u'refreshed_at', TIMESTAMP(timezone=True))

    #relationship definitions


class SocorroDbVersionHistory(DeclarativeBase):
    __tablename__ = 'socorro_db_version_history'

    __table_args__ = {}

    #column definitions
    backfill_to = Column(u'backfill_to', DATE())
    upgraded_on = Column(u'upgraded_on', TIMESTAMP(timezone=True), primary_key=True, nullable=False, default=text('NOW()'))
    version = Column(u'version', TEXT(), primary_key=True, nullable=False)

    #relationship definitions


class SpecialProductPlatform(DeclarativeBase):
    __tablename__ = 'special_product_platforms'

    __table_args__ = {}

    #column definitions
    min_version = Column(u'min_version', TEXT())
    platform = Column(u'platform', CITEXT(), primary_key=True, nullable=False)
    product_name = Column(u'product_name', CITEXT(), nullable=False)
    release_channel = Column(u'release_channel', CITEXT(), primary_key=True, nullable=False)
    release_name = Column(u'release_name', CITEXT(), primary_key=True, nullable=False)
    repository = Column(u'repository', CITEXT(), primary_key=True, nullable=False)

    #relationship definitions

class TcbsBuild(DeclarativeBase):
    __tablename__ = 'tcbs_build'

    __table_args__ = {}

    #column definitions
    build_date = Column(u'build_date', DATE(), primary_key=True, nullable=False)
    hang_count = Column(u'hang_count', INTEGER(), nullable=False, default=0)
    lin_count = Column(u'lin_count', INTEGER(), nullable=False, default=0)
    mac_count = Column(u'mac_count', INTEGER(), nullable=False, default=0)
    process_type = Column(u'process_type', CITEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    release_channel = Column(u'release_channel', CITEXT(), nullable=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, default=0)
    report_date = Column(u'report_date', DATE(), primary_key=True, nullable=False)
    signature_id = Column(u'signature_id', INTEGER(), primary_key=True, nullable=False)
    startup_count = Column(u'startup_count', INTEGER())
    win_count = Column(u'win_count', INTEGER(), nullable=False, default=0)

    #relationship definitions


class TransformRule(DeclarativeBase):
    __tablename__ = 'transform_rules'

    __table_args__ = {}

    #column definitions
    transform_rule_id = Column(u'transform_rule_id', INTEGER(), primary_key=True, nullable=False)
    category = Column(u'category', CITEXT(), nullable=False)
    rule_order = Column(u'rule_order', INTEGER(), nullable=False)
    action = Column(u'action', TEXT(), nullable=False, default='')
    action_args = Column(u'action_args', TEXT(), nullable=False, default='')
    action_kwargs = Column(u'action_kwargs', TEXT(), nullable=False, default='')
    predicate = Column(u'predicate', TEXT(), nullable=False, default='')
    predicate_args = Column(u'predicate_args', TEXT(), nullable=False, default='')
    predicate_kwargs = Column(u'predicate_kwargs', TEXT(), nullable=False, default='')

    #relationship definitions


class UptimeLevel(DeclarativeBase):
    __tablename__ = 'uptime_levels'

    __table_args__ = {}

    #column definitions
    max_uptime = Column(u'max_uptime', INTERVAL(), nullable=False)
    min_uptime = Column(u'min_uptime', INTERVAL(), nullable=False)
    uptime_level = Column(u'uptime_level', INTEGER(), primary_key=True, nullable=False)
    uptime_string = Column(u'uptime_string', CITEXT(), nullable=False)

    #relationship definitions


class PostgreSQLManager(object):
    def __init__(self, dsn, logger):
        self.conn = psycopg2.connect(dsn)
        self.conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.logger = logger

    def execute(self, sql, allowable_errors=None):
        cur = self.conn.cursor()
        try:
            cur.execute(sql)
        except ProgrammingError, e:
            if not allowable_errors:
                raise
            dberr = e.pgerror.strip().split('ERROR:  ')[1]
            for err in allowable_errors:
                if re.match(err, dberr):
                    self.logger.warning(dberr)
                else:
                    raise

    def version(self):
        cur = self.conn.cursor()
        cur.execute("SELECT version()")
        version_info = cur.fetchall()[0][0].split()
        return version_info[1]

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.conn.close()


class SocorroDB(App):
    app_name = 'setupdb'
    app_version = '0.2'
    app_description = __doc__

    required_config = Namespace()

    required_config.add_option(
        name='database_name',
        default='',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='database_hostname',
        default='',
        doc='Hostname to connect to database',
    )

    required_config.add_option(
        name='database_username',
        default='',
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_password',
        default='',
        doc='Password to connect to database',
    )

    required_config.add_option(
        name='database_port',
        default='',
        doc='Port to connect to database',
    )

    required_config.add_option(
        name='dropdb',
        default=False,
        doc='Whether or not to drop database_name',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    required_config.add_option(
        name='no_schema',
        default=False,
        doc='Whether or not to load schema',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    required_config.add_option(
        name='citext',
        default='/usr/share/postgresql/9.0/contrib/citext.sql',
        doc='Name of citext.sql file',
    )

    def main(self):

        self.database_name = self.config['database_name']
        if not self.database_name:
            print "Syntax error: --database_name required"
            return 1

        self.no_schema = self.config.get('no_schema')
        self.citext = self.config.get('citext')

        dsn_template = 'dbname=%s'
        url_template = 'postgresql://'

        self.database_username = self.config.get('database_username')
        if self.database_username:
            dsn_template += ' user=%s' % self.database_username
            url_template += '%s' % self.database_username
        self.database_password = self.config.get('database_password')
        if self.database_password:
            dsn_template += ' password=%s' % self.database_password
            url_template += ':%s' % self.database_password
        self.database_hostname = self.config.get('database_hostname')
        if self.database_hostname:
            dsn_template += ' host=%s' % self.database_hostname
            url_template += '@%s' % self.database_hostname
        self.database_port = self.config.get('database_port')
        if self.database_port:
            dsn_template += ' port=%s' % self.database_port
            url_template += ':%s' % self.database_port

        dsn = dsn_template % 'template1'

        with PostgreSQLManager(dsn, self.config.logger) as db:
            db_version = db.version()
            if not re.match(r'9\.[2][.*]', db_version):
                print 'ERROR - unrecognized PostgreSQL vesion: %s' % db_version
                print 'Only 9.2 is supported at this time'
                return 1
            if self.config.get('dropdb'):
                if 'test' not in self.database_name:
                    confirm = raw_input(
                        'drop database %s [y/N]: ' % self.database_name)
                    if not confirm == "y":
                        logging.warn('NOT dropping table')
                        return 2

                db.execute('DROP DATABASE %s' % self.database_name,
                    ['database "%s" does not exist' % self.database_name])
                db.execute('DROP SCHEMA pgx_diag',
                           ['schema "pgx_diag" does not exist'])

            try:
                db.execute('CREATE DATABASE %s' % self.database_name)
            except ProgrammingError, e:
                if re.match(
                       'database "%s" already exists' % self.database_name,
                       e.pgerror.strip().split('ERROR:  ')[1]):
                    # already done, no need to rerun
                    print "The DB %s already exists" % self.database_name
                    return 0
                raise

        #dsn = dsn_template % self.database_name
        sa_url = url_template + '/%s' % self.database_name

        self.engine = create_engine(sa_url)
        self.session = sessionmaker(bind=self.engine)()
        self.engine.connect()
        metadata = DeclarativeBase.metadata
        metadata.bind = self.engine
        metadata.create_all(self.engine)
        self.session.execute('ALTER DATABASE %s OWNER TO breakpad_rw'
                        % self.database_name)
        self.session.commit()

        return 0

if __name__ == "__main__":
    sys.exit(main(SocorroDB))

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
from sqlalchemy import event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import sqlalchemy.types as types
try:
    from sqlalchemy.dialects.postgresql import *
except ImportError:
    from sqlalchemy.databases.postgres import *

#######################################
# Create CITEXT type for SQL Alchemy
#######################################

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


###########################################
# Baseclass for all Socorro tables
###########################################

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata


###############################
# Schema definition: Tables
###############################

email_campaigns_contacts = Table(u'email_campaigns_contacts', metadata,
    Column(u'email_campaigns_id', INTEGER(), ForeignKey('email_campaigns.id')),
    Column(u'email_contacts_id', INTEGER(), ForeignKey('email_contacts.id')),
    Column(u'status', TEXT(), nullable=False, server_default='stopped'),
)

product_release_channels = Table(u'product_release_channels', metadata,
    Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), primary_key=True, nullable=False),
    Column(u'release_channel', CITEXT(), ForeignKey('release_channels.release_channel'), primary_key=True, nullable=False),
    Column(u'throttle', NUMERIC(), nullable=False, server_default=text('1.0')),
)

product_versions = Table(u'product_versions', metadata,
    Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False),
    Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), nullable=False),
    Column(u'major_version', TEXT()),
    Column(u'release_version', CITEXT(), nullable=False),
    Column(u'version_string', CITEXT(), nullable=False),
    Column(u'beta_number', INTEGER()),
    Column(u'version_sort', TEXT(), nullable=False, server_default="0"),
    Column(u'build_date', DATE(), nullable=False),
    Column(u'sunset_date', DATE(), nullable=False),
    Column(u'featured_version', BOOLEAN(), nullable=False, server_default=text('False')),
    Column(u'build_type', CITEXT(), nullable=False, server_default='release'),
    Column(u'has_builds', BOOLEAN()),
    Column(u'is_rapid_beta', BOOLEAN(), server_default=text('False')),
    Column(u'rapid_beta_id', INTEGER(), ForeignKey('product_versions.product_version_id')),
)

signature_products_rollup = Table(u'signature_products_rollup', metadata,
    Column(u'signature_id', INTEGER(), ForeignKey('signatures.signature_id'), primary_key=True, nullable=False),
    Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), primary_key=True, nullable=False),
    Column(u'ver_count', INTEGER(), nullable=False, server_default=text('0')),
    Column(u'version_list', ARRAY(TEXT()), nullable=False, server_default=text("'{}'::text[]")),
)

tcbses = Table(u'tcbs', metadata,
    Column(u'signature_id', INTEGER(), ForeignKey('signatures.signature_id'), primary_key=True, nullable=False),
    Column(u'report_date', DATE(), primary_key=True, nullable=False),
    Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False),
    Column(u'process_type', CITEXT(), primary_key=True, nullable=False),
    Column(u'release_channel', CITEXT(), ForeignKey('release_channels.release_channel'), primary_key=True, nullable=False),
    Column(u'report_count', INTEGER(), nullable=False, server_default=text('0')),
    Column(u'win_count', INTEGER(), nullable=False, server_default=text('0')),
    Column(u'mac_count', INTEGER(), nullable=False, server_default=text('0')),
    Column(u'lin_count', INTEGER(), nullable=False, server_default=text('0')),
    Column(u'hang_count', INTEGER(), nullable=False, server_default=text('0')),
    Column(u'startup_count', INTEGER()),
)

correlation_addons = Table(u'correlation_addons', metadata,
    Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False),
    Column(u'addon_key', TEXT(), nullable=False),
    Column(u'addon_version', TEXT(), nullable=False),
    Column(u'crash_count', INTEGER(), nullable=False, server_default=text('0')),
)

correlation_cores = Table(u'correlation_cores', metadata,
    Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False),
    Column(u'architecture', CITEXT(), nullable=False),
    Column(u'cores', INTEGER(), nullable=False),
    Column(u'crash_count', INTEGER(), nullable=False, server_default=text('0')),
)

correlation_modules = Table(u'correlation_modules', metadata,
    Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False),
    Column(u'module_signature', TEXT(), nullable=False),
    Column(u'module_version', TEXT(), nullable=False),
    Column(u'crash_count', INTEGER(), nullable=False, server_default=text('0')),
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
    address_id = Column(u'address_id', INTEGER(), primary_key=True, nullable=False)
    address = Column(u'address', CITEXT(), nullable=False)
    first_seen = Column(u'first_seen', TIMESTAMP(timezone=True))

    #relationship definitions


class Bug(DeclarativeBase):
    __tablename__ = 'bugs'

    __table_args__ = {}

    #column definitions
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    status = Column(u'status', TEXT())
    resolution = Column(u'resolution', TEXT())
    short_desc = Column(u'short_desc', TEXT())

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
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
    build_date = Column(u'build_date', DATE(), primary_key=True, nullable=False)
    adu_date = Column(u'adu_date', DATE(), primary_key=True, nullable=False)
    os_name = Column(u'os_name', CITEXT(), primary_key=True, nullable=False)
    adu_count = Column(u'adu_count', INTEGER(), nullable=False)

    #relationship definitions


class Correlations(DeclarativeBase):
    __tablename__ = 'correlations'

    __table_args__ = {}

    #column definitions
    correlation_id = Column(u'correlation_id', INTEGER(), primary_key=True, nullable=False)
    crash_count = Column(u'crash_count', INTEGER(), nullable=False, server_default=text('0'))
    os_name = Column(u'os_name', CITEXT(), nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), nullable=False, autoincrement=False)
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
    include_agg = Column(u'include_agg', BOOLEAN(), nullable=False, server_default=text('True'))
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
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
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
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
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
    product_version_id = Column(u'product_version_id', INTEGER(), nullable=False, autoincrement=False)
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
    date_created = Column(u'date_created', TIMESTAMP(timezone=True), nullable=False, server_default=text('NOW()'))
    email_count = Column(u'email_count', INTEGER(), server_default=text('0'))
    end_date = Column(u'end_date', TIMESTAMP(timezone=True), nullable=False)
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    product = Column(u'product', TEXT(), nullable=False)
    signature = Column(u'signature', TEXT(), nullable=False)
    start_date = Column(u'start_date', TIMESTAMP(timezone=True), nullable=False)
    status = Column(u'status', TEXT(), nullable=False, server_default='stopped')
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
    subscribe_status = Column(u'subscribe_status', BOOLEAN(), server_default=text('True'))
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
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
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
    adu = Column(u'adu', INTEGER(), nullable=False, server_default=text('0'))
    crash_hadu = Column(u'crash_hadu', NUMERIC(), nullable=False, server_default=text('0.0'))
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, server_default=text('0'))
    report_date = Column(u'report_date', DATE(), primary_key=True, nullable=False)

    #relationship definitions


class HomePageGraphBuild(DeclarativeBase):
    __tablename__ = 'home_page_graph_build'

    __table_args__ = {}

    #column definitions
    adu = Column(u'adu', INTEGER(), nullable=False, server_default=text('0'))
    build_date = Column(u'build_date', DATE(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, server_default=text('0'))
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
    priority = Column(u'priority', INTEGER(), server_default=text('0'))
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
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, server_default=text('0'))
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
    sort = Column(u'sort', SMALLINT(), nullable=False, server_default=text('0'))

    #relationship definitions
    release_channels = relationship('ReleaseChannel', primaryjoin='Product.product_name==ProductReleaseChannel.product_name', secondary=product_release_channels, secondaryjoin='ProductReleaseChannel.release_channel==ReleaseChannel.release_channel')
    product_versions = relationship('ProductVersion', primaryjoin='Product.product_name==ProductVersion.product_name', secondary=product_versions, secondaryjoin='ProductVersion.rapid_beta_id==ProductVersion.product_version_id')
    signatures = relationship('Signature', primaryjoin='Product.product_name==SignatureProductsRollup.product_name', secondary=signature_products_rollup, secondaryjoin='SignatureProductsRollup.signature_id==Signature.signature_id')


class ProductAdu(DeclarativeBase):
    __tablename__ = 'product_adu'

    __table_args__ = {}

    #column definitions
    adu_count = Column(u'adu_count', BIGINT(), nullable=False, server_default=text('0'))
    adu_date = Column(u'adu_date', DATE(), primary_key=True, nullable=False)
    os_name = Column(u'os_name', CITEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)

    #relationship definitions


class ProductProductidMap(DeclarativeBase):
    __tablename__ = 'product_productid_map'

    __table_args__ = {}

    #column definitions
    product_name = Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), nullable=False)
    productid = Column(u'productid', TEXT(), primary_key=True, nullable=False)
    rewrite = Column(u'rewrite', BOOLEAN(), nullable=False, server_default=text('False'))
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
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
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
    sort = Column(u'sort', SMALLINT(), nullable=False, server_default=text('0'))

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
    repository = Column(u'repository', CITEXT(), primary_key=True, nullable=False, server_default='mozilla-release')
    version = Column(u'version', TEXT(), primary_key=True, nullable=False)

    #relationship definitions


class ReportPartitionInfo(DeclarativeBase):
    __tablename__ = 'report_partition_info'

    __table_args__ = {}

    #column definitions
    build_order = Column(u'build_order', INTEGER(), nullable=False, server_default=text('1'))
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
    product_version_id = Column(u'product_version_id', INTEGER(), autoincrement=False)
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
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
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
    upgraded_on = Column(u'upgraded_on', TIMESTAMP(timezone=True), primary_key=True, nullable=False, server_default=text('NOW()'))
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
    hang_count = Column(u'hang_count', INTEGER(), nullable=False, server_default=text('0'))
    lin_count = Column(u'lin_count', INTEGER(), nullable=False, server_default=text('0'))
    mac_count = Column(u'mac_count', INTEGER(), nullable=False, server_default=text('0'))
    process_type = Column(u'process_type', CITEXT(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
    release_channel = Column(u'release_channel', CITEXT(), nullable=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, server_default=text('0'))
    report_date = Column(u'report_date', DATE(), primary_key=True, nullable=False)
    signature_id = Column(u'signature_id', INTEGER(), primary_key=True, nullable=False)
    startup_count = Column(u'startup_count', INTEGER())
    win_count = Column(u'win_count', INTEGER(), nullable=False, server_default=text('0'))

    #relationship definitions


class TransformRule(DeclarativeBase):
    __tablename__ = 'transform_rules'

    __table_args__ = {}

    #column definitions
    transform_rule_id = Column(u'transform_rule_id', INTEGER(), primary_key=True, nullable=False)
    category = Column(u'category', CITEXT(), nullable=False)
    rule_order = Column(u'rule_order', INTEGER(), nullable=False)
    action = Column(u'action', TEXT(), nullable=False, server_default='')
    action_args = Column(u'action_args', TEXT(), nullable=False, server_default='')
    action_kwargs = Column(u'action_kwargs', TEXT(), nullable=False, server_default='')
    predicate = Column(u'predicate', TEXT(), nullable=False, server_default='')
    predicate_args = Column(u'predicate_args', TEXT(), nullable=False, server_default='')
    predicate_kwargs = Column(u'predicate_kwargs', TEXT(), nullable=False, server_default='')

    #relationship definitions


class UptimeLevel(DeclarativeBase):
    __tablename__ = 'uptime_levels'

    __table_args__ = {}

    #column definitions
    max_uptime = Column(u'max_uptime', INTERVAL(), nullable=False)
    min_uptime = Column(u'min_uptime', INTERVAL(), nullable=False)
    uptime_level = Column(u'uptime_level', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
    uptime_string = Column(u'uptime_string', CITEXT(), nullable=False)

    #relationship definitions


###########################################
##  Special, non-table schema objects
###########################################

###########################################
##  Schema definition: Aggregates
###########################################

@event.listens_for(UptimeLevel.__table__, "after_create")
def array_accum(target, connection, **kw):
    array_accum = """
CREATE AGGREGATE array_accum(anyelement) (
    SFUNC = array_append,
    STYPE = anyarray,
    INITCOND = '{}'
)
"""
    connection.execute(array_accum)

@event.listens_for(UptimeLevel.__table__, "after_create")
def content_count(target, connection, **kw):
    content_count = """
CREATE AGGREGATE content_count(citext, integer) (
    SFUNC = content_count_state,
    STYPE = integer,
    INITCOND = '0'
)
"""
    connection.execute(content_count)

@event.listens_for(UptimeLevel.__table__, "after_create")
def plugin_count(target, connection, **kw):
    plugin_count = """
CREATE AGGREGATE plugin_count(citext, integer) (
    SFUNC = plugin_count_state,
    STYPE = integer,
    INITCOND = '0'
)
"""
    connection.execute(plugin_count)


###########################################
##  Schema definition: Types
###########################################

@event.listens_for(UptimeLevel.__table__, "before_create")
def create_socorro_types(target, connection, **kw):
# Special types
    flash_process_dump_type = """
CREATE TYPE flash_process_dump_type AS ENUM (
    'Sandbox',
    'Broker'
)
"""
    connection.execute(flash_process_dump_type)
    product_info_change = """
CREATE TYPE product_info_change AS (
	begin_date date,
	end_date date,
	featured boolean,
	crash_throttle numeric
)
"""
    connection.execute(product_info_change)
    release_enum = """
CREATE TYPE release_enum AS ENUM (
    'major',
    'milestone',
    'development'
)
"""
    connection.execute(release_enum)


###########################################
##  Schema definition: Domains
###########################################

@event.listens_for(UptimeLevel.__table__, "before_create")
def create_socorro_domains(target, connection, **kw):
    major_version = """
CREATE DOMAIN major_version AS text
	CONSTRAINT major_version_check CHECK ((VALUE ~ '^\d+\.\d+'::text))
"""
    connection.execute(major_version)


#####################################################
## User Defined Functions in PostgreSQL
#####################################################

@event.listens_for(UptimeLevel.__table__, "before_create")
def add_column_if_not_exists(target, connection, **kw):
	add_column_if_not_exists = """
CREATE FUNCTION add_column_if_not_exists(tablename text, columnname text, datatype text, nonnull boolean DEFAULT false, defaultval text DEFAULT ''::text, constrainttext text DEFAULT ''::text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- support function for creating new columns idempotently
-- does not check data type for changes
-- allows constraints and defaults; beware of using
-- these against large tables!
-- if the column already exists, does not check for
-- the constraints and defaults

-- validate input
IF nonnull AND ( defaultval = '' ) THEN
	RAISE EXCEPTION 'for NOT NULL columns, you must add a default';
END IF;

IF defaultval <> '' THEN
	defaultval := ' DEFAULT ' || quote_literal(defaultval);
END IF;

-- check if the column already exists.
PERFORM 1 
FROM information_schema.columns
WHERE table_name = tablename
	AND column_name = columnname;
	
IF FOUND THEN
	RETURN FALSE;
END IF;

EXECUTE 'ALTER TABLE ' || tablename ||
	' ADD COLUMN ' || columnname ||
	' ' || datatype || defaultval;

IF nonnull THEN
	EXECUTE 'ALTER TABLE ' || tablename ||
		' ALTER COLUMN ' || columnname ||
		|| ' SET NOT NULL;';
END IF;

IF constrainttext <> '' THEn
	EXECUTE 'ALTER TABLE ' || tablename ||
		' ADD CONSTRAINT ' || constrainttext;
END IF;

RETURN TRUE;

END;$$
"""
	connection.execute(add_column_if_not_exists)

@event.listens_for(UptimeLevel.__table__, "before_create")
def add_new_product(target, connection, **kw):
	add_new_product = """
CREATE FUNCTION add_new_product(prodname text, initversion major_version, prodid text DEFAULT NULL::text, ftpname text DEFAULT NULL::text, release_throttle numeric DEFAULT 1.0) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare current_sort int;
	rel_name text;
begin

IF prodname IS NULL OR initversion IS NULL THEN
	RAISE EXCEPTION 'a product name and initial version are required';
END IF;

-- check if product already exists
PERFORM 1 FROM products
WHERE product_name = prodname;

IF FOUND THEN
	RAISE INFO 'product %% is already in the database';
	RETURN FALSE;
END IF;

-- add the product
SELECT max(sort) INTO current_sort
FROM products;

INSERT INTO products ( product_name, sort, rapid_release_version,
	release_name )
VALUES ( prodname, current_sort + 1, initversion,
	COALESCE(ftpname, prodname));

-- add the release channels

INSERT INTO product_release_channels ( product_name, release_channel )
SELECT prodname, release_channel
FROM release_channels;

-- if throttling, change throttle for release versions

IF release_throttle < 1.0 THEN

	UPDATE product_release_channels
	SET throttle = release_throttle
	WHERE product_name = prodname
		AND release_channel = 'release';

END IF;

-- add the productid map

IF prodid IS NOT NULL THEN
	INSERT INTO product_productid_map ( product_name,
		productid, version_began )
	VALUES ( prodname, prodid, initversion );
END IF;

RETURN TRUE;

END;$$
"""
	connection.execute(add_new_product)

@event.listens_for(UptimeLevel.__table__, "before_create")
def add_new_release(target, connection, **kw):
	add_new_release = """
CREATE FUNCTION add_new_release(product citext, version citext, release_channel citext, build_id numeric, platform citext, beta_number integer DEFAULT NULL::integer, repository text DEFAULT 'release'::text, update_products boolean DEFAULT false, ignore_duplicates boolean DEFAULT false) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE rname citext;
BEGIN
-- adds a new release to the releases_raw table
-- to be picked up by update_products later
-- does some light format validation

-- check for NULLs, blanks
IF NOT ( nonzero_string(product) AND nonzero_string(version)
	AND nonzero_string(release_channel) and nonzero_string(platform)
	AND build_id IS NOT NULL ) THEN
	RAISE EXCEPTION 'product, version, release_channel, platform and build ID are all required';
END IF;

-- product
-- what we get could be a product name or a release name.  depending, we want to insert the
-- release name
SELECT release_name INTO rname
FROM products WHERE release_name = product;
IF rname IS NULL THEN
	SELECT release_name INTO rname
	FROM products WHERE product_name = product;
	IF rname IS NULL THEN
		RAISE EXCEPTION 'You must supply a valid product or product release name';
	END IF;
END IF;

--validate channel
PERFORM validate_lookup('release_channels','release_channel',release_channel,'release channel');
--validate build
IF NOT ( build_date(build_id) BETWEEN '2005-01-01'
	AND (current_date + INTERVAL '1 month') ) THEN
	RAISE EXCEPTION 'invalid buildid';
END IF;

--add row
--duplicate check will occur in the EXECEPTION section
INSERT INTO releases_raw (
	product_name, version, platform, build_id,
	build_type, beta_number, repository )
VALUES ( rname, version, platform, build_id,
	release_channel, beta_number, repository );

--call update_products, if desired
IF update_products THEN
	PERFORM update_product_versions();
END IF;

--return
RETURN TRUE;

--exception clause, mainly catches duplicate rows.
EXCEPTION
	WHEN UNIQUE_VIOLATION THEN
		IF ignore_duplicates THEN
			RETURN FALSE;
		ELSE
			RAISE EXCEPTION 'the release you have entered is already present in he database';
		END IF;
END;$$
"""
	connection.execute(add_new_release)

@event.listens_for(UptimeLevel.__table__, "before_create")
def add_old_release(target, connection, **kw):
	add_old_release = """
CREATE FUNCTION add_old_release(product_name text, new_version text, release_type release_enum DEFAULT 'major'::release_enum, release_date date DEFAULT ('now'::text)::date, is_featured boolean DEFAULT false) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE last_date DATE;
featured_count INT;
new_id INT;
BEGIN

IF release_type = 'major' THEN
last_date := release_date + ( 18 * 7 );
ELSE
last_date := release_date + ( 9 * 7 );
END IF;

IF is_featured THEN
-- check if we already have 4 featured
SELECT COUNT(*) INTO featured_count
FROM productdims JOIN product_visibility
ON productdims.id = product_visibility.productdims_id
WHERE featured
AND product = product_name
AND end_date >= current_date;

IF featured_count > 4 THEN
-- too many, drop one
UPDATE product_visibility
SET featured = false
WHERE productdims_id = (
SELECT id
FROM productdims
JOIN product_visibility viz2
ON productdims.id = viz2.productdims_id
WHERE product = product_name
AND featured
AND end_date >= current_date
ORDER BY viz2.end_date LIMIT 1
);
END IF;
END IF;

    -- now add it
    
    INSERT INTO productdims ( product, version, branch, release, version_sort )
    VALUES ( product_name, new_version, '2.2', release_type, old_version_sort(new_version) )
    RETURNING id
    INTO new_id;
    
    INSERT INTO product_visibility ( productdims_id, start_date, end_date,
    featured, throttle )
    VALUES ( new_id, release_date, last_date, is_featured, 100 );
    
    RETURN TRUE;
    
END; $$
"""
	connection.execute(add_old_release)

@event.listens_for(UptimeLevel.__table__, "before_create")
def aurora_or_nightly(target, connection, **kw):
	aurora_or_nightly = """
CREATE FUNCTION aurora_or_nightly(version text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
-- figures out "aurora" or "nightly" from a version string
-- returns ERROR otherwise
SELECT CASE WHEN $1 LIKE '%%a1' THEN 'nightly'
	WHEN $1 LIKE '%%a2' THEN 'aurora'
	ELSE 'ERROR' END;
$_$
"""
	connection.execute(aurora_or_nightly)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_adu(target, connection, **kw):
	backfill_adu = """
CREATE FUNCTION backfill_adu(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- stored procudure to delete and replace one day of
-- product_adu, optionally only for a specific product
-- intended to be called by backfill_matviews

DELETE FROM product_adu
WHERE adu_date = updateday;

PERFORM update_adu(updateday, false);

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_adu)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_all_dups(target, connection, **kw):
	backfill_all_dups = """
CREATE FUNCTION backfill_all_dups(start_date timestamp without time zone, end_date timestamp without time zone) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare this_time timestamp;
	dups_found int;
begin

this_time := start_date + interval '1 hour';

	create temporary table new_reports_duplicates (
		uuid text, duplicate_of text, date_processed timestamp )
		on commit drop;

-- fill in duplicates for one-hour windows
-- advancing in 30-minute increments
while this_time <= end_date loop

	dups_found := backfill_reports_duplicates( this_time - INTERVAL '1 hour', this_time);
	
	RAISE INFO '%% duplicates found for %%',dups_found,this_time;

	this_time := this_time + interval '30 minutes';
	
	-- analyze once per day, just to avoid bad query plans
	IF extract('hour' FROM this_time) = 2 THEN
		analyze reports_duplicates;
	END IF;
	
	truncate new_reports_duplicates;

end loop;

return true;
end; $$
"""
	connection.execute(backfill_all_dups)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_build_adu(target, connection, **kw):
	backfill_build_adu = """
CREATE FUNCTION backfill_build_adu(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM build_adu WHERE adu_date = updateday;
PERFORM update_build_adu(updateday, false);

RETURN TRUE;
END; $$;
"""
	connection.execute(backfill_build_adu)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_correlations(target, connection, **kw):
	backfill_correlations = """
CREATE FUNCTION backfill_correlations(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

PERFORM update_correlations(updateday, false);

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_correlations)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_crashes_by_user(target, connection, **kw):
	backfill_crashes_by_user = """
CREATE FUNCTION backfill_crashes_by_user(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM crashes_by_user WHERE report_date = updateday;
PERFORM update_crashes_by_user(updateday, false, check_period);

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_crashes_by_user)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_crashes_by_user_build(target, connection, **kw):
	backfill_crashes_by_user_build = """
CREATE FUNCTION backfill_crashes_by_user_build(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM crashes_by_user_build WHERE report_date = updateday;
PERFORM update_crashes_by_user_build(updateday, false, check_period);

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_crashes_by_user_build)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_daily_crashes(target, connection, **kw):
	backfill_daily_crashes = """
CREATE FUNCTION backfill_daily_crashes(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN
-- VERSION 4
-- deletes and replaces daily_crashes for selected dates
-- now just nests a call to update_daily_crashes

DELETE FROM daily_crashes
WHERE adu_day = updateday;
PERFORM update_daily_crashes(updateday, false);

RETURN TRUE;

END;$$
"""
	connection.execute(backfill_daily_crashes)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_explosiveness(target, connection, **kw):
	backfill_explosiveness = """
CREATE FUNCTION backfill_explosiveness(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

PERFORM update_explosiveness(updateday, false);
DROP TABLE IF EXISTS crash_madu;
DROP TABLE IF EXISTS xtab_mult;
DROP TABLE IF EXISTS crash_xtab;
DROP TABLE IF EXISTS explosive_oneday;
DROP TABLE IF EXISTS explosive_threeday;

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_explosiveness)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_hang_report(target, connection, **kw):
	backfill_hang_report = """
CREATE FUNCTION backfill_hang_report(backfilldate date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- delete rows
DELETE FROM daily_hangs
WHERE report_date = backfilldate;

PERFORM update_hang_report(backfilldate, false);
RETURN TRUE;

END;
$$
"""
	connection.execute(backfill_hang_report)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_home_page_graph(target, connection, **kw):
	backfill_home_page_graph = """
CREATE FUNCTION backfill_home_page_graph(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM home_page_graph WHERE report_date = updateday;
PERFORM update_home_page_graph(updateday, false, check_period);

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_home_page_graph)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_home_page_graph_build(target, connection, **kw):
	backfill_home_page_graph_build = """
CREATE FUNCTION backfill_home_page_graph_build(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM home_page_graph_build WHERE report_date = updateday;
PERFORM update_home_page_graph_build(updateday, false, check_period);

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_home_page_graph_build)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_matviews(target, connection, **kw):
	backfill_matviews = """
CREATE FUNCTION backfill_matviews(firstday date, lastday date DEFAULT NULL::date, reportsclean boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
    AS $$
DECLARE thisday DATE := firstday;
	last_rc timestamptz;
	first_rc timestamptz;
	last_adu DATE;
BEGIN
-- this producedure is meant to be called manually
-- by administrators in order to clear and backfill
-- the various matviews in order to recalculate old
-- data which was erroneous.
-- it requires a start date, and optionally an end date
-- no longer takes a product parameter
-- optionally disable reports_clean backfill
-- since that takes a long time

-- this is a temporary fix for matview backfill for mobeta
-- a more complete fix is coming in 19.0.

-- set start date for r_c
first_rc := firstday AT TIME ZONE 'UTC';

-- check parameters
IF firstday > current_date OR lastday > current_date THEN
	RAISE EXCEPTION 'date parameter error: cannot backfill into the future';
END IF;

-- set optional end date
IF lastday IS NULL or lastday = current_date THEN
	last_rc := date_trunc('hour', now()) - INTERVAL '3 hours';
ELSE
	last_rc := ( lastday + 1 ) AT TIME ZONE 'UTC';
END IF;

-- check if lastday is after we have ADU;
-- if so, adjust lastday
SELECT max("date")
INTO last_adu
FROM raw_adu;

IF lastday > last_adu THEN
	RAISE INFO 'last day of backfill period is after final day of ADU.  adjusting last day to %%',last_adu;
	lastday := last_adu;
END IF;

-- fill in products
PERFORM update_product_versions();

-- backfill reports_clean.  this takes a while
-- we provide a switch to disable it
IF reportsclean THEN
	RAISE INFO 'backfilling reports_clean';
	PERFORM backfill_reports_clean( first_rc, last_rc );
END IF;

-- loop through the days, backfilling one at a time
WHILE thisday <= lastday LOOP
	RAISE INFO 'backfilling other matviews for %%',thisday;
	RAISE INFO 'adu';
	PERFORM backfill_adu(thisday);
	PERFORM backfill_build_adu(thisday);
	RAISE INFO 'signatures';
	PERFORM update_signatures(thisday, FALSE);
	RAISE INFO 'tcbs';
	PERFORM backfill_tcbs(thisday);
	PERFORM backfill_tcbs_build(thisday);
	DROP TABLE IF EXISTS new_tcbs;
	RAISE INFO 'crashes by user';
	PERFORM backfill_crashes_by_user(thisday);
	PERFORM backfill_crashes_by_user_build(thisday);
	RAISE INFO 'home page graph';
	PERFORM backfill_home_page_graph(thisday);
	PERFORM backfill_home_page_graph_build(thisday);
	DROP TABLE IF EXISTS new_signatures;
	RAISE INFO 'hang report (slow)';
	PERFORM backfill_hang_report(thisday);
	RAISE INFO 'nightly builds';
	PERFORM backfill_nightly_builds(thisday);

	thisday := thisday + 1;

END LOOP;

-- finally rank_compare and correlations, which don't need to be filled in for each day
RAISE INFO 'rank_compare';
PERFORM backfill_rank_compare(lastday);
RAISE INFO 'explosiveness (slow)';
PERFORM backfill_explosiveness(thisday);
RAISE INFO 'correlations';
PERFORM backfill_correlations(lastday);

RETURN true;
END; $$
"""
	connection.execute(backfill_matviews)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_nightly_builds(target, connection, **kw):
	backfill_nightly_builds = """
CREATE FUNCTION backfill_nightly_builds(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM nightly_builds WHERE report_date = updateday;
PERFORM update_nightly_builds(updateday, false);

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_nightly_builds)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_one_day(target, connection, **kw):
	backfill_one_day = """
CREATE FUNCTION backfill_one_day() RETURNS text
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
declare datematch text;
  reppartition text;
  bkdate date;
begin

  SELECT last_date + 1 INTO bkdate
  FROM last_backfill_temp;

  IF bkdate > '2011-08-04' THEN
    RETURN 'done';
  END IF;

  datematch := to_char(bkdate, 'YYMMDD');

  create temporary table back_one_day
  on commit drop as
  select * from releasechannel_backfill
  where uuid LIKE ( '%%' || datematch );

  create index back_one_day_idx ON back_one_day(uuid);

  raise info 'temp table created';

  select relname into reppartition
  from pg_stat_user_tables
  where relname like 'reports_2011%%'
    and relname <= ( 'reports_20' || datematch )
  order by relname desc limit 1;

  raise info 'updating %%',reppartition;
  
  EXECUTE 'UPDATE ' || reppartition || ' SET release_channel = back_one_day.release_channel
    FROM back_one_day WHERE back_one_day.uuid = ' || reppartition || '.uuid;';

  UPDATE last_backfill_temp SET last_date = bkdate;

  RETURN reppartition;

END; $$
"""
	connection.execute(backfill_one_day)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_one_day(target, connection, **kw):
	backfill_one_day = """
CREATE FUNCTION backfill_one_day(bkdate date) RETURNS text
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
declare datematch text;
  reppartition text;
begin

  IF bkdate > '2011-08-04' THEN
    RETURN 'done';
  END IF;

  datematch := to_char(bkdate, 'YYMMDD');

  create temporary table back_one_day
  on commit drop as
  select * from releasechannel_backfill
  where uuid LIKE ( '%%' || datematch );

  create index back_one_day_idx ON back_one_day(uuid);

  raise info 'temp table created';

  select relname into reppartition
  from pg_stat_user_tables
  where relname like 'reports_2011%%'
    and relname <= ( 'reports_20' || datematch )
  order by relname desc limit 1;

  raise info 'updating %%',reppartition;
  
  EXECUTE 'UPDATE ' || reppartition || ' SET release_channel = back_one_day.release_channel
    FROM back_one_day WHERE back_one_day.uuid = ' || reppartition || '.uuid;';

  UPDATE last_backfill_temp SET last_date = bkdate;

  RETURN reppartition;

END; $$
"""
	connection.execute(backfill_one_day)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_rank_compare(target, connection, **kw):
	backfill_rank_compare = """
CREATE FUNCTION backfill_rank_compare(updateday date DEFAULT NULL::date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

PERFORM update_rank_compare(updateday, false);

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_rank_compare)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_reports_clean(target, connection, **kw):
	backfill_reports_clean = """
CREATE FUNCTION backfill_reports_clean(begin_time timestamp with time zone, end_time timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- administrative utility for backfilling reports_clean to the selected date
-- intended to be called on the command line
-- uses a larger cycle (6 hours) if we have to backfill several days of data
-- note that this takes timestamptz as parameters
-- otherwise call backfill_reports_clean_by_date.
DECLARE cyclesize INTERVAL := '1 hour';
	stop_time timestamptz;
	cur_time timestamptz := begin_time;
BEGIN
	IF end_time IS NULL OR end_time > ( now() - interval '3 hours' ) THEN
	-- if no end time supplied, then default to three hours ago
	-- on the hour
		stop_time := ( date_trunc('hour', now()) - interval '3 hours' );
	ELSE
		stop_time := end_time;
	END IF;

	IF ( COALESCE(end_time, now()) - begin_time ) > interval '15 hours' THEN
		cyclesize := '6 hours';
	END IF;

	WHILE cur_time < stop_time LOOP
		IF cur_time + cyclesize > stop_time THEN
			cyclesize = stop_time - cur_time;
		END IF;

		RAISE INFO 'backfilling %% of reports_clean starting at %%',cyclesize,cur_time;

		DELETE FROM reports_clean
		WHERE date_processed >= cur_time
			AND date_processed < ( cur_time + cyclesize );

		DELETE FROM reports_user_info
		WHERE date_processed >= cur_time
			AND date_processed < ( cur_time + cyclesize );

		PERFORM update_reports_clean( cur_time, cyclesize, false );

		cur_time := cur_time + cyclesize;
	END LOOP;

	RETURN TRUE;
END;$$
"""
	connection.execute(backfill_reports_clean)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_reports_duplicates(target, connection, **kw):
	backfill_reports_duplicates = """
CREATE FUNCTION backfill_reports_duplicates(start_time timestamp without time zone, end_time timestamp without time zone) RETURNS integer
    LANGUAGE plpgsql
    SET work_mem TO '256MB'
    SET temp_buffers TO '128MB'
    AS $$
declare new_dups INT;
begin

-- create a temporary table with the new duplicates
-- for the hour
-- this query contains the duplicate-finding algorithm
-- so it will probably change frequently

insert into new_reports_duplicates
select follower.uuid as uuid,
	leader.uuid as duplicate_of,
	follower.date_processed
from
(  
select uuid,
    install_age,
    uptime,
    client_crash_date,
    date_processed,
  first_value(uuid)
  over ( partition by
            product,
            version,
            build,
            signature,
            cpu_name,
            cpu_info,
            os_name,
            os_version,
            address,
            topmost_filenames,
            reason,
            app_notes,
            url
         order by
            client_crash_date,
            uuid
        ) as leader_uuid
   from reports
   where date_processed BETWEEN start_time AND end_time
 ) as follower
JOIN 
  ( select uuid, install_age, uptime, client_crash_date
    FROM reports
    where date_processed BETWEEN start_time AND end_time ) as leader
  ON follower.leader_uuid = leader.uuid
WHERE ( same_time_fuzzy(leader.client_crash_date, follower.client_crash_date, 
                  leader.uptime, follower.uptime) 
		  OR follower.uptime < 60 
  	  )
  AND
	same_time_fuzzy(leader.client_crash_date, follower.client_crash_date, 
                  leader.install_age, follower.install_age)
  AND follower.uuid <> leader.uuid;
  
-- insert a copy of the leaders
  
insert into new_reports_duplicates
select uuid, uuid, date_processed
from reports
where uuid IN ( select duplicate_of 
	from new_reports_duplicates )
	and date_processed BETWEEN start_time AND end_time;
  
analyze new_reports_duplicates;

select count(*) into new_dups from new_reports_duplicates;

-- insert new duplicates into permanent table

insert into reports_duplicates (uuid, duplicate_of, date_processed )
select new_reports_duplicates.* 
from new_reports_duplicates
	left outer join reports_duplicates USING (uuid)
where reports_duplicates.uuid IS NULL;

-- done return number of dups found and exit
RETURN new_dups;
end;$$
"""
	connection.execute(backfill_reports_duplicates)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_signature_counts(target, connection, **kw):
	backfill_signature_counts = """
CREATE FUNCTION backfill_signature_counts(begindate date, enddate date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE thisdate DATE := begindate;
BEGIN

WHILE thisdate <= enddate LOOP

	RAISE INFO 'backfilling %%',thisdate;

	DELETE FROM os_signature_counts WHERE report_date = thisdate;
	DELETE FROM product_signature_counts WHERE report_date = thisdate;
	DELETE FROM uptime_signature_counts WHERE report_date = thisdate;
	PERFORM update_os_signature_counts(thisdate, false);
	PERFORM update_product_signature_counts(thisdate, false);
	PERFORM update_uptime_signature_counts(thisdate, false);
	
	thisdate := thisdate + 1;
	
END LOOP;

RETURN TRUE;
END; $$
"""
	connection.execute(backfill_signature_counts)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_tcbs(target, connection, **kw):
	backfill_tcbs = """
CREATE FUNCTION backfill_tcbs(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of TCBS
-- designed to be called by backfill_matviews
DELETE FROM tcbs WHERE report_date = updateday;
PERFORM update_tcbs(updateday, false, check_period);

RETURN TRUE;
END;$$
"""
	connection.execute(backfill_tcbs)

@event.listens_for(UptimeLevel.__table__, "before_create")
def backfill_tcbs_build(target, connection, **kw):
	backfill_tcbs_build = """
CREATE FUNCTION backfill_tcbs_build(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of TCBS
-- designed to be called by backfill_matviews
DELETE FROM tcbs_build WHERE report_date = updateday;
PERFORM update_tcbs_build(updateday, false, check_period);

RETURN TRUE;
END;$$
"""
	connection.execute(backfill_tcbs_build)

@event.listens_for(UptimeLevel.__table__, "before_create")
def build_date(target, connection, **kw):
	build_date = """
CREATE FUNCTION build_date(build_id numeric) RETURNS date
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts build number to a date
SELECT to_date(substr( $1::text, 1, 8 ),'YYYYMMDD');
$_$
"""
	connection.execute(build_date)

@event.listens_for(UptimeLevel.__table__, "before_create")
def build_numeric(target, connection, **kw):
	build_numeric = """
CREATE FUNCTION build_numeric(character varying) RETURNS numeric
    LANGUAGE sql STRICT
    AS $_$
-- safely converts a build number to a numeric type
-- if the build is not a number, returns NULL
SELECT CASE WHEN $1 ~ $x$^\d+$$x$ THEN
	$1::numeric
ELSE
	NULL::numeric
END;$_$
"""
	connection.execute(build_numeric)

@event.listens_for(UptimeLevel.__table__, "before_create")
def check_partitions(target, connection, **kw):
	check_partitions = """
CREATE FUNCTION check_partitions(tables text[], numpartitions integer, OUT result integer, OUT data text) RETURNS record
    LANGUAGE plpgsql
    AS $$
DECLARE cur_partition TEXT;
partcount INT;
msg TEXT := '';
thistable TEXT;
BEGIN

result := 0;
cur_partition := to_char(now(),'YYYYMMDD');
-- tables := ARRAY['reports','extensions','frames','plugin_reports'];

FOR thistable IN SELECT * FROM unnest(tables) LOOP

SELECT count(*) INTO partcount
FROM pg_stat_user_tables
WHERE relname LIKE ( thistable || '_%%' )  
AND relname > ( thistable || '_' || cur_partition );

--RAISE INFO '%% : %%',thistable,partcount;

IF partcount < numpartitions OR partcount IS NULL THEN 
result := result + 1;
msg := msg || ' ' || thistable;
END IF;

END LOOP;

IF result > 0 THEN
data := 'Some tables have no future partitions:' || msg;
END IF;

RETURN;

END; $$
"""
	connection.execute(check_partitions)

@event.listens_for(UptimeLevel.__table__, "before_create")
def content_count_state(target, connection, **kw):
	content_count_state = """
CREATE FUNCTION content_count_state(running_count integer, process_type citext, crash_count integer) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $_$
-- allows us to do a content crash count
-- horizontally as well as vertically on tcbs
SELECT CASE WHEN $2 = 'content' THEN
  coalesce($3,0) + $1
ELSE
  $1
END; $_$
"""
	connection.execute(content_count_state)

@event.listens_for(UptimeLevel.__table__, "before_create")
def crash_hadu(target, connection, **kw):
	crash_hadu = """
CREATE FUNCTION crash_hadu(crashes bigint, adu bigint, throttle numeric DEFAULT 1.0) RETURNS numeric
    LANGUAGE sql
    AS $_$
SELECT CASE WHEN $2 = 0 THEN 0::numeric
ELSE
	round( ( $1 * 100::numeric / $2 ) / $3, 3)
END;
$_$
"""
	connection.execute(crash_hadu)

@event.listens_for(UptimeLevel.__table__, "before_create")
def crash_hadu(target, connection, **kw):
	crash_hadu = """
CREATE FUNCTION crash_hadu(crashes bigint, adu numeric, throttle numeric DEFAULT 1.0) RETURNS numeric
    LANGUAGE sql
    AS $_$
SELECT CASE WHEN $2 = 0 THEN 0::numeric
ELSE
	round( ( $1 * 100::numeric / $2 ) / $3, 3)
END;
$_$
"""
	connection.execute(crash_hadu)

@event.listens_for(UptimeLevel.__table__, "before_create")
def create_os_version_string(target, connection, **kw):
	create_os_version_string = """
CREATE FUNCTION create_os_version_string(osname citext, major integer, minor integer) RETURNS citext
    LANGUAGE plpgsql STABLE STRICT
    AS $$
DECLARE winversion CITEXT;
BEGIN
	-- small function which produces a user-friendly
	-- string for the operating system and version
	-- if windows, look it up in windows_versions
	IF osname = 'Windows' THEN
		SELECT windows_version_name INTO winversion
		FROM windows_versions
		WHERE major_version = major AND minor_version = minor;
		IF NOT FOUND THEN
			RETURN 'Windows Unknown';
		ELSE
			RETURN winversion;
		END IF;
	ELSEIF osname = 'Mac OS X' THEN
	-- if mac, then concatinate unless the numbers are impossible
		IF major BETWEEN 10 and 11 AND minor BETWEEN 0 and 20 THEN
			RETURN 'OS X ' || major || '.' || minor;
		ELSE
			RETURN 'OS X Unknown';
		END IF;
	ELSE
	-- for other oses, just use the OS name
		RETURN osname;
	END IF;
END; $$
"""
	connection.execute(create_os_version_string)

@event.listens_for(UptimeLevel.__table__, "before_create")
def create_table_if_not_exists(target, connection, **kw):
	create_table_if_not_exists = """
CREATE FUNCTION create_table_if_not_exists(tablename text, declaration text, tableowner text DEFAULT ''::text, indexes text[] DEFAULT '{}'::text[]) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE dex INT := 1;
	scripts TEXT[] := '{}';
	indexname TEXT;
BEGIN
-- this function allows you to send a create table script to the backend 
-- multiple times without erroring.  it checks if the table is already
-- there and also optionally sets the ownership
-- this version of the function also creates indexes from a list of fields
	PERFORM 1 FROM pg_stat_user_tables
	WHERE relname = tablename;
	IF FOUND THEN
		RETURN TRUE;
	ELSE
		scripts := string_to_array(declaration, ';');
		WHILE scripts[dex] IS NOT NULL LOOP
			EXECUTE scripts[dex];
			dex := dex + 1;
		END LOOP;
	END IF;
	
	IF tableowner <> '' THEN
		EXECUTE 'ALTER TABLE ' || tablename || ' OWNER TO ' || tableowner;
	END IF;
	
	dex := 1;
	
	WHILE indexes[dex] IS NOT NULL LOOP
		indexname := replace( indexes[dex], ',', '_' );
		indexname := replace ( indexname, ' ', '' );
		EXECUTE 'CREATE INDEX ' || tablename || '_' || indexname || 
			' ON ' || tablename || '(' || indexes[dex] || ')';
		dex := dex + 1;
	END LOOP;
	
	EXECUTE 'ANALYZE ' || tablename;
	
	RETURN TRUE;
END;
$$
"""
	connection.execute(create_table_if_not_exists)

@event.listens_for(UptimeLevel.__table__, "before_create")
def create_weekly_partition(target, connection, **kw):
	create_weekly_partition = """
CREATE FUNCTION create_weekly_partition(tablename citext, theweek date, partcol text DEFAULT 'date_processed'::text, tableowner text DEFAULT ''::text, uniques text[] DEFAULT '{}'::text[], indexes text[] DEFAULT '{}'::text[], fkeys text[] DEFAULT '{}'::text[], is_utc boolean DEFAULT false, timetype text DEFAULT 'TIMESTAMP'::text) RETURNS boolean
    LANGUAGE plpgsql
    AS $_$
DECLARE dex INT := 1;
	thispart TEXT;
	zonestring TEXT := '';
	fkstring TEXT;
BEGIN
-- this function allows you to create a new weekly partition
-- of an existing master table.  it checks if the table is already
-- there and also optionally sets the ownership
-- this version of the function also creates indexes from a list of fields
-- currently only handles single-column indexes and unique declarations
-- supports date, timestamp, timestamptz/utc through the various options

	thispart := tablename || '_' || to_char(theweek, 'YYYYMMDD');
	
	PERFORM 1 FROM pg_stat_user_tables
	WHERE relname = thispart;
	IF FOUND THEN
		RETURN TRUE;
	END IF;
	
	IF is_utc THEN
		timetype := ' TIMESTAMP';
		zonestring := ' AT TIME ZONE UTC ';
	END IF;
	
	EXECUTE 'CREATE TABLE ' || thispart || ' ( CONSTRAINT ' || thispart 
		|| '_date_check CHECK ( ' || partcol || ' BETWEEN ' 
		|| timetype || ' ' || quote_literal(to_char(theweek, 'YYYY-MM-DD'))
		|| ' AND ' || timetype || ' ' 
		|| quote_literal(to_char(theweek + 7, 'YYYY-MM-DD'))
		|| ' ) ) INHERITS ( ' || tablename || ');';
	
	IF tableowner <> '' THEN
		EXECUTE 'ALTER TABLE ' || thispart || ' OWNER TO ' || tableowner;
	END IF;
	
	dex := 1;
	WHILE uniques[dex] IS NOT NULL LOOP
		EXECUTE 'CREATE UNIQUE INDEX ' || thispart || '_'
		|| regexp_replace(uniques[dex], $$[,\s]+$$, '_', 'g') 
		|| ' ON ' || thispart || '(' || uniques[dex] || ')';
		dex := dex + 1;
	END LOOP;
	
	dex := 1;
	WHILE indexes[dex] IS NOT NULL LOOP
		EXECUTE 'CREATE INDEX ' || thispart || '_' 
		|| regexp_replace(indexes[dex], $$[,\s]+$$, '_', 'g') 
		|| ' ON ' || thispart || '(' || indexes[dex] || ')';
		dex := dex + 1;
	END LOOP;
	
	dex := 1;
	WHILE fkeys[dex] IS NOT NULL LOOP
		fkstring := regexp_replace(fkeys[dex], 'WEEKNUM', to_char(theweek, 'YYYYMMDD'), 'g');
		EXECUTE 'ALTER TABLE ' || thispart || ' ADD CONSTRAINT ' 
			|| thispart || '_fk_' || dex || ' FOREIGN KEY '
			|| fkstring || ' ON DELETE CASCADE ON UPDATE CASCADE';
		dex := dex + 1;
	END LOOP;
	
	RETURN TRUE;
END;
$_$
"""
	connection.execute(create_weekly_partition)

@event.listens_for(UptimeLevel.__table__, "before_create")
def crontabber_nodelete(target, connection, **kw):
	crontabber_nodelete = """
CREATE FUNCTION crontabber_nodelete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN

	RAISE EXCEPTION 'you are not allowed to add or delete records from the crontabber table';

END;
$$
"""
	connection.execute(crontabber_nodelete)

@event.listens_for(UptimeLevel.__table__, "before_create")
def crontabber_timestamp(target, connection, **kw):
	crontabber_timestamp = """
CREATE FUNCTION crontabber_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	
	NEW.last_updated = now();
	RETURN NEW;
	
END; $$
"""
	connection.execute(crontabber_timestamp)

@event.listens_for(UptimeLevel.__table__, "before_create")
def daily_crash_code(target, connection, **kw):
	daily_crash_code = """
CREATE FUNCTION daily_crash_code(process_type text, hangid text) RETURNS character
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT CASE
	WHEN $1 ILIKE 'content' THEN 'T'
	WHEN ( $1 IS NULL OR $1 ILIKE 'browser' ) AND $2 IS NULL THEN 'C'
	WHEN ( $1 IS NULL OR $1 ILIKE 'browser' ) AND $2 IS NOT NULL THEN 'c'
	WHEN $1 ILIKE 'plugin' AND $2 IS NULL THEN 'P'
	WHEN $1 ILIKE 'plugin' AND $2 IS NOT NULL THEN 'p'
	ELSE 'C'
	END
$_$
"""
	connection.execute(daily_crash_code)

@event.listens_for(UptimeLevel.__table__, "before_create")
def drop_old_partitions(target, connection, **kw):
	drop_old_partitions = """
CREATE FUNCTION drop_old_partitions(mastername text, cutoffdate date) RETURNS boolean
    LANGUAGE plpgsql
    AS $_X$
DECLARE tabname TEXT;
	listnames TEXT;
BEGIN
listnames := $q$SELECT relname FROM pg_stat_user_tables
		WHERE relname LIKE '$q$ || mastername || $q$_%%' 
		AND relname < '$q$ || mastername || '_' 
		|| to_char(cutoffdate, 'YYYYMMDD') || $q$'$q$;

IF try_lock_table(mastername,'ACCESS EXCLUSIVE') THEN
	FOR tabname IN EXECUTE listnames LOOP
		
		EXECUTE 'DROP TABLE ' || tabname;
		
	END LOOP;
ELSE
	RAISE EXCEPTION 'Unable to lock table plugin_reports; try again later';
END IF;
RETURN TRUE;
END;
$_X$
"""
	connection.execute(drop_old_partitions)

@event.listens_for(UptimeLevel.__table__, "before_create")
def edit_featured_versions(target, connection, **kw):
	edit_featured_versions = """
CREATE FUNCTION edit_featured_versions(product citext, VARIADIC featured_versions text[]) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function allows admins to change the featured versions
-- for a particular product
BEGIN

--check required parameters
IF NOT ( nonzero_string(product) AND nonzero_string(featured_versions[1]) ) THEN
	RAISE EXCEPTION 'a product name and at least one version are required';
END IF;

--check that all versions are not expired
PERFORM 1 FROM product_versions
WHERE product_name = product
  AND version_string = ANY ( featured_versions )
  AND sunset_date < current_date;
IF FOUND THEN
	RAISE EXCEPTION 'one or more of the versions you have selected is already expired';
END IF;

--Remove disfeatured versions
UPDATE product_versions SET featured_version = false
WHERE featured_version
	AND product_name = product
	AND NOT ( version_string = ANY( featured_versions ) );
	
--feature new versions
UPDATE product_versions SET featured_version = true
WHERE version_string = ANY ( featured_versions )
	AND product_name = product
	AND NOT featured_version;

RETURN TRUE;

END;$$
"""
	connection.execute(edit_featured_versions)

@event.listens_for(UptimeLevel.__table__, "before_create")
def edit_product_info(target, connection, **kw):
    # version_sort_digit
	version_sort_digit = """
CREATE FUNCTION version_sort_digit(digit text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts an individual part of a version number
-- into a three-digit sortable string
SELECT CASE WHEN $1 <> '' THEN
	to_char($1::INT,'FM000')
	ELSE '000' END;
$_$
"""
	connection.execute(version_sort_digit)
    # major_version_sort and deps
	major_version_sort = """
CREATE FUNCTION major_version_sort(version text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts a major_version string into a padded,
-- sortable string
select version_sort_digit( substring($1 from $x$^(\d+)$x$) )
	|| version_sort_digit( substring($1 from $x$^\d+\.(\d+)$x$) );
$_$
"""
	connection.execute(major_version_sort)

	is_rapid_beta = """
CREATE FUNCTION is_rapid_beta(channel citext, repversion text, rbetaversion text) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT $1 = 'beta' AND major_version_sort($2) >= major_version_sort($3);
$_$
"""
	connection.execute(is_rapid_beta)

	edit_product_info = """
CREATE FUNCTION edit_product_info(prod_id integer, prod_name citext, prod_version text, prod_channel text, begin_visibility date, end_visibility date, is_featured boolean, crash_throttle numeric, user_name text DEFAULT ''::text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE which_t text;
	new_id INT;
	oldrec product_info_change;
	newrec product_info_change;
-- this function allows the admin UI to edit product and version
-- information regardless of which table it appears in
-- currently editing the new products is limited to
-- visibility dates and featured because of the need to supply
-- build numbers, and that we're not sure it will ever
-- be required.
-- does not validate required fields or duplicates
-- trusting to the python code and table constraints to do that

-- will be phased out when we can ignore the old productdims

BEGIN

IF prod_id IS NULL THEN
-- new entry
-- adding rows is only allowed to the old table since the new
-- table is populated automatically
-- see if this is supposed to be in the new table and error out
	PERFORM 1
	FROM products
	WHERE product_name = prod_name
		AND major_version_sort(prod_version) >= major_version_sort(rapid_release_version);
	IF FOUND AND prod_version NOT LIKE '%%a%%' THEN
		RAISE EXCEPTION 'Product %% version %% will be automatically updated by the new system.  As such, you may not add this product & version manually.',prod_name,prod_version;
	ELSE

		INSERT INTO productdims ( product, version, branch, release )
		VALUES ( prod_name, prod_version, '2.2',
			CASE WHEN prod_channel ILIKE 'beta' THEN 'milestone'::release_enum
				WHEN prod_channel ILIKE 'aurora' THEN 'development'::release_enum
				WHEN prod_channel ILIKE 'nightly' THEN 'development'::release_enum
				ELSE 'major' END )
		RETURNING id
		INTO new_id;

		INSERT INTO product_visibility ( productdims_id, start_date, end_date, featured, throttle )
		VALUES ( new_id, begin_visibility, end_visibility, is_featured, crash_throttle );

	END IF;

ELSE

-- first, find out whether we're dealing with the old or new table
	SELECT which_table INTO which_t
	FROM product_info WHERE product_version_id = prod_id;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'No product with that ID was found.  Database Error.';
	END IF;

	IF which_t = 'new' THEN
		-- note that changes to the product name or version will be ignored
		-- only changes to featured and visibility dates will be taken
		
		-- first we're going to log this since we've had some issues
		-- and we want to track updates
		INSERT INTO product_info_changelog (
			product_version_id, user_name, changed_on,
			oldrec, newrec )
		SELECT prod_id, user_name, now(),
			row( build_date, sunset_date,
				featured_version, throttle )::product_info_change,
			row( begin_visibility, end_visibility, 
				is_featured, crash_throttle/100 )::product_info_change
		FROM product_versions JOIN product_release_channels
			ON product_versions.product_name = product_release_channels.product_name
			AND product_versions.build_type = product_release_channels.release_channel
		WHERE product_version_id = prod_id;
		
		-- then update
		UPDATE product_versions SET
			featured_version = is_featured,
			build_date = begin_visibility,
			sunset_date = end_visibility
		WHERE product_version_id = prod_id;

		UPDATE product_release_channels
		SET throttle = crash_throttle / 100
		WHERE product_name = prod_name
			AND release_channel = prod_channel;

		new_id := prod_id;
	ELSE
		UPDATE productdims SET
			product = prod_name,
			version = prod_version,
			release = ( CASE WHEN prod_channel ILIKE 'beta' THEN 'milestone'::release_enum
				WHEN prod_channel ILIKE 'aurora' THEN 'development'::release_enum
				WHEN prod_channel ILIKE 'nightly' THEN 'development'::release_enum
				ELSE 'major' END )
		WHERE id = prod_id;

		UPDATE product_visibility SET
			featured = is_featured,
			start_date = begin_visibility,
			end_date = end_visibility,
			throttle = crash_throttle
		WHERE productdims_id = prod_id;

		new_id := prod_id;
	END IF;
END IF;

RETURN new_id;
END; $$
"""
	connection.execute(edit_product_info)

@event.listens_for(UptimeLevel.__table__, "before_create")
def get_cores(target, connection, **kw):
	get_cores = """
CREATE FUNCTION get_cores(cpudetails text) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT substring($1 from $x$\| (\d+)$$x$)::INT;
$_$
"""
	connection.execute(get_cores)

@event.listens_for(ProductVersion.__table__, "after_create")
def get_product_version_ids(target, connection, **kw):
	get_product_version_ids = """
CREATE FUNCTION get_product_version_ids(product citext, VARIADIC versions citext[]) RETURNS integer[]
    LANGUAGE sql
    AS $_$
SELECT array_agg(product_version_id) 
FROM product_versions
	WHERE product_name = $1
	AND version_string = ANY ( $2 );
$_$
"""
	connection.execute(get_product_version_ids)

@event.listens_for(UptimeLevel.__table__, "before_create")
def initcap(target, connection, **kw):
	initcap = """
CREATE FUNCTION initcap(text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT upper(substr($1,1,1)) || substr($1,2);
$_$
"""
	connection.execute(initcap)

#@event.listens_for(.__table__, "before_create")

@event.listens_for(UptimeLevel.__table__, "before_create")
def last_record(target, connection, **kw):
	last_record = """
CREATE FUNCTION last_record(tablename text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
declare curdate timestamp;
  resdate timestamp;
  ressecs integer;
begin

CASE WHEN tablename = 'reports' THEN
  curdate:= now() - INTERVAL '3 days';
  EXECUTE 'SELECT max(date_processed)
  FROM reports
  WHERE date_processed > ' || 
        quote_literal(to_char(curdate, 'YYYY-MM-DD')) 
        || ' and date_processed < ' ||
        quote_literal(to_char(curdate + INTERVAL '4 days','YYYY-MM-DD'))
    INTO resdate;
  IF resdate IS NULL THEN
     resdate := curdate;
  END IF;
WHEN tablename = 'top_crashes_by_signature' THEN
  SELECT max(window_end)
  INTO resdate
  FROM top_crashes_by_signature;
WHEN tablename = 'top_crashes_by_url' THEN
  SELECT max(window_end)
  INTO resdate
  FROM top_crashes_by_url;
ELSE
  resdate:= null;
END CASE;

ressecs := round(EXTRACT('epoch' FROM ( now() - resdate )))::INT;

RETURN ressecs;

END;$$
"""
	connection.execute(last_record)

@event.listens_for(UptimeLevel.__table__, "before_create")
def log_priorityjobs(target, connection, **kw):
	log_priorityjobs = """
CREATE FUNCTION log_priorityjobs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
declare arewelogging boolean;
begin
SELECT log_jobs INTO arewelogging
FROM priorityjobs_logging_switch;
IF arewelogging THEN 
INSERT INTO priorityjobs_log VALUES ( NEW.uuid );
END IF;
RETURN NEW;
end; $$
"""
	connection.execute(log_priorityjobs)

@event.listens_for(UptimeLevel.__table__, "before_create")
def major_version(target, connection, **kw):
	major_version = """
CREATE FUNCTION major_version(version text) RETURNS major_version
    LANGUAGE sql IMMUTABLE
    AS $_$
-- turns a version string into a major version
-- i.e. "6.0a2" into "6.0"
SELECT substring($1 from $x$^(\d+.\d+)$x$)::major_version;
$_$
"""
	connection.execute(major_version)

@event.listens_for(UptimeLevel.__table__, "before_create")
def nonzero_string(target, connection, **kw):
	nonzero_string = """
CREATE FUNCTION nonzero_string(citext) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$_$
"""
	connection.execute(nonzero_string)

@event.listens_for(UptimeLevel.__table__, "before_create")
def nonzero_string(target, connection, **kw):
	nonzero_string = """
CREATE FUNCTION nonzero_string(text) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$_$
"""
	connection.execute(nonzero_string)

@event.listens_for(UptimeLevel.__table__, "before_create")
def old_version_sort(target, connection, **kw):
	old_version_sort = """
CREATE FUNCTION old_version_sort(vers text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT to_char( matched[1]::int, 'FM000' )
	|| to_char( matched[2]::int, 'FM000' )
	|| to_char( coalesce( matched[4]::int, 0 ), 'FM000' )
	|| CASE WHEN matched[3] <> '' THEN 'b'
		WHEN matched[5] <> '' THEN 'b'
		ELSE 'z' END
	|| '000'
FROM ( SELECT regexp_matches($1,
$x$^(\d+)[^\d]*\.(\d+)([a-z]?)[^\.]*(?:\.(\d+))?([a-z]?).*$$x$) as matched) as match 
LIMIT 1;
$_$
"""
	connection.execute(old_version_sort)

@event.listens_for(UptimeLevel.__table__, "before_create")
def pacific2ts(target, connection, **kw):
	pacific2ts = """
CREATE FUNCTION pacific2ts(timestamp with time zone) RETURNS timestamp without time zone
    LANGUAGE sql STABLE
    SET "TimeZone" TO 'America/Los_Angeles'
    AS $_$
SELECT $1::timestamp;
$_$
"""
	connection.execute(pacific2ts)

@event.listens_for(UptimeLevel.__table__, "before_create")
def plugin_count_state(target, connection, **kw):
	plugin_count_state = """
CREATE FUNCTION plugin_count_state(running_count integer, process_type citext, crash_count integer) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $_$
-- allows us to do a plugn count horizontally
-- as well as vertically on tcbs
SELECT CASE WHEN $2 = 'plugin' THEN
  coalesce($3,0) + $1
ELSE
  $1
END; $_$
"""
	connection.execute(plugin_count_state)

@event.listens_for(UptimeLevel.__table__, "before_create")
def product_version_sort_number(target, connection, **kw):
	product_version_sort_number = """
CREATE FUNCTION product_version_sort_number(sproduct text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- reorders the product-version list for a specific
-- product after an update
-- we just reorder the whole group rather than doing
-- something more fine-tuned because it's actually less
-- work for the database and more foolproof.

UPDATE productdims SET sort_key = new_sort
FROM  ( SELECT product, version, 
row_number() over ( partition by product
order by sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
extra ASC NULLS FIRST)
as new_sort
 FROM productdims_version_sort
 WHERE product = sproduct )
AS product_resort
WHERE productdims.product = product_resort.product
AND productdims.version = product_resort.version
AND ( sort_key <> new_sort OR sort_key IS NULL );

RETURN TRUE;
END;$$
"""
	connection.execute(product_version_sort_number)

@event.listens_for(UptimeLevel.__table__, "before_create")
def reports_clean_done(target, connection, **kw):
	reports_clean_done = """
CREATE FUNCTION reports_clean_done(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function checks that reports_clean has been updated
-- all the way to the last hour of the UTC day
BEGIN

PERFORM 1
    FROM reports_clean
    WHERE date_processed BETWEEN ( ( updateday::timestamp at time zone 'utc' )
            +  ( interval '24 hours' - check_period ) )
        AND ( ( updateday::timestamp at time zone 'utc' ) + interval '1 day' )
    LIMIT 1;
IF FOUND THEN
    RETURN TRUE;
ELSE
    RETURN FALSE;
END IF;
END; $$
"""
	connection.execute(reports_clean_done)

@event.listens_for(UptimeLevel.__table__, "before_create")
def reports_clean_weekly_partition(target, connection, **kw):
	reports_clean_weekly_partition = """
CREATE FUNCTION reports_clean_weekly_partition(this_date timestamp with time zone, which_table text) RETURNS text
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
    AS $_$
-- this function, meant to be called internally
-- checks if the correct reports_clean or reports_user_info partition exists
-- otherwise it creates it
-- returns the name of the partition
declare this_part text;
	begin_week text;
	end_week text;
	rc_indexes text[];
	dex int := 1;
begin
	this_part := which_table || '_' || to_char(date_trunc('week', this_date), 'YYYYMMDD');
	begin_week := to_char(date_trunc('week', this_date), 'YYYY-MM-DD');
	end_week := to_char(date_trunc('week', this_date) + interval '1 week', 'YYYY-MM-DD');
	
	PERFORM 1
	FROM pg_stat_user_tables
	WHERE relname = this_part;
	IF FOUND THEN
		RETURN this_part;
	END IF;
	
	EXECUTE 'CREATE TABLE ' || this_part || $$
		( CONSTRAINT date_processed_week CHECK ( date_processed >= '$$ || begin_week || $$'::timestamp AT TIME ZONE 'UTC'
			AND date_processed < '$$ || end_week || $$'::timestamp AT TIME ZONE 'UTC' ) )
		INHERITS ( $$ || which_table || $$ );$$;
	EXECUTE 'CREATE UNIQUE INDEX ' || this_part || '_uuid ON ' || this_part || '(uuid);';

	IF which_table = 'reports_clean' THEN

		rc_indexes := ARRAY[ 'date_processed', 'product_version_id', 'os_name', 'os_version_id', 
			'signature_id', 'address_id', 'flash_version_id', 'hang_id', 'process_type', 'release_channel', 'domain_id' ];
			
		EXECUTE 'CREATE INDEX ' || this_part || '_sig_prod_date ON ' || this_part 
			|| '( signature_id, product_version_id, date_processed )';
			
		EXECUTE 'CREATE INDEX ' || this_part || '_arch_cores ON ' || this_part 
			|| '( architecture, cores )';
			
	ELSEIF which_table = 'reports_user_info' THEN
	
		rc_indexes := '{}';
	
	END IF;
	
	WHILE rc_indexes[dex] IS NOT NULL LOOP
		EXECUTE 'CREATE INDEX ' || this_part || '_' || rc_indexes[dex]
			|| ' ON ' || this_part || '(' || rc_indexes[dex] || ');';
		dex := dex + 1;
	END LOOP;
	
	EXECUTE 'ALTER TABLE ' || this_part || ' OWNER TO breakpad_rw';
	
	RETURN this_part;
end;$_$
"""
	connection.execute(reports_clean_weekly_partition)

@event.listens_for(UptimeLevel.__table__, "before_create")
def same_time_fuzzy(target, connection, **kw):
	same_time_fuzzy = """
CREATE FUNCTION same_time_fuzzy(date1 timestamp with time zone, date2 timestamp with time zone, interval_secs1 integer, interval_secs2 integer) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT
-- return true if either interval is null
-- so we don't exclude crashes missing data
CASE WHEN $3 IS NULL THEN
	TRUE
WHEN $4 IS NULL THEN
	TRUE
-- otherwise check that the two timestamp deltas
-- and the two interval deltas are within 60 sec
-- of each other
ELSE
	(
		extract ('epoch' from ( $2 - $1 ) ) -
		( $4 - $3 ) 
	) BETWEEN -60 AND 60
END;
$_$
"""
	connection.execute(same_time_fuzzy)

@event.listens_for(UptimeLevel.__table__, "before_create")
def socorro_db_data_refresh(target, connection, **kw):
	socorro_db_data_refresh = """
CREATE FUNCTION socorro_db_data_refresh(refreshtime timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS timestamp with time zone
    LANGUAGE sql
    AS $_$
UPDATE socorro_db_version SET refreshed_at = COALESCE($1, now())
RETURNING refreshed_at;
$_$
"""
	connection.execute(socorro_db_data_refresh)

@event.listens_for(UptimeLevel.__table__, "before_create")
def sunset_date(target, connection, **kw):
	sunset_date = """
CREATE FUNCTION sunset_date(build_id numeric, build_type citext) RETURNS date
    LANGUAGE sql IMMUTABLE
    AS $_$
-- sets a sunset date for visibility
-- based on a build number
-- current spec is 18 weeks for releases
-- 9 weeks for everything else
select ( build_date($1) +
	case when $2 = 'release'
		then interval '18 weeks'
	when $2 = 'ESR'
		then interval '18 weeks'
	else
		interval '9 weeks'
	end ) :: date
$_$
"""
	connection.execute(sunset_date)

# TODO this didn't get created for some reason!
@event.listens_for(UptimeLevel.__table__, "before_create")
def to_major_version(target, connection, **kw):
	to_major_version = """
CREATE FUNCTION to_major_version(version text) RETURNS major_version
    LANGUAGE sql IMMUTABLE
    AS $_$
-- turns a version string into a major version
-- i.e. "6.0a2" into "6.0"
SELECT substring($1 from $x$^(\d+\.\d+)$x$)::major_version;
$_$
"""
	connection.execute(to_major_version)

@event.listens_for(UptimeLevel.__table__, "before_create")
def transform_rules_insert_order(target, connection, **kw):
	transform_rules_insert_order = """
CREATE FUNCTION transform_rules_insert_order() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE order_num INT;
-- this trigger function makes sure that all rules have a unique order
-- within their category, and assigns an order number to new rules
BEGIN
	IF NEW.rule_order IS NULL or NEW.rule_order = 0 THEN
		-- no order supplied, add the rule to the end
		SELECT max(rule_order) 
		INTO order_num
		FROM transform_rules
		WHERE category = NEW.category;
		
		NEW.rule_order := COALESCE(order_num, 0) + 1;
	ELSE
		-- check if there's already a gap there
		PERFORM rule_order 
		FROM transform_rules
		WHERE category = NEW.category
			AND rule_order = NEW.rule_order;
		-- if not, then bump up
		IF FOUND THEN
			UPDATE transform_rules 
			SET rule_order = rule_order + 1
			WHERE category = NEW.category
				AND rule_order = NEW.rule_order;
		END IF;
	END IF;

	RETURN NEW;
END;
$$
"""
	connection.execute(transform_rules_insert_order)

@event.listens_for(UptimeLevel.__table__, "before_create")
def transform_rules_update_order(target, connection, **kw):
	transform_rules_update_order = """
CREATE FUNCTION transform_rules_update_order() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	-- if we've changed the order number, or category reorder
	IF NEW.rule_order <> OLD.rule_order 
		OR NEW.category <> OLD.category THEN
				
		-- insert a new gap
		UPDATE transform_rules
		SET rule_order = rule_order + 1
		WHERE category = NEW.category
			AND rule_order = NEW.rule_order
			AND transform_rule_id <> NEW.transform_rule_id;
	
	END IF;	
		
	RETURN NEW;
END;
$$
"""
	connection.execute(transform_rules_update_order)

@event.listens_for(UptimeLevel.__table__, "before_create")
def try_lock_table(target, connection, **kw):
	try_lock_table = """
CREATE FUNCTION try_lock_table(tabname text, mode text DEFAULT 'EXCLUSIVE'::text, attempts integer DEFAULT 20) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function tries to lock a table
-- in a loop, retrying every 3 seconds for 20 tries
-- until it gets a lock
-- or gives up
-- returns true if the table is locked, false
-- if unable to lock
DECLARE loopno INT := 1;
BEGIN
	WHILE loopno < attempts LOOP
		BEGIN
			EXECUTE 'LOCK TABLE ' || tabname || ' IN ' || mode || ' MODE NOWAIT';
			RETURN TRUE;
		EXCEPTION
			WHEN LOCK_NOT_AVAILABLE THEN
				PERFORM pg_sleep(3);
				CONTINUE;
		END;
	END LOOP;
RETURN FALSE;
END;$$
"""
	connection.execute(try_lock_table)

@event.listens_for(UptimeLevel.__table__, "before_create")
def tstz_between(target, connection, **kw):
	tstz_between = """
CREATE FUNCTION tstz_between(tstz timestamp with time zone, bdate date, fdate date) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT $1 >= ( $2::timestamp AT TIME ZONE 'UTC' ) 
	AND $1 < ( ( $3 + 1 )::timestamp AT TIME ZONE 'UTC' );
$_$
"""
	connection.execute(tstz_between)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_adu(target, connection, **kw):
	update_adu = """
CREATE FUNCTION update_adu(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN
-- daily batch update procedure to update the
-- adu-product matview, used to power graphs
-- gets its data from raw_adu, which is populated
-- daily by metrics

-- check if raw_adu has been updated.  otherwise, abort.
PERFORM 1 FROM raw_adu
WHERE "date" = updateday
LIMIT 1;

IF NOT FOUND THEN
    IF checkdata THEN
        RAISE EXCEPTION 'raw_adu not updated for %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check if ADU has already been run for the date
PERFORM 1 FROM product_adu
WHERE adu_date = updateday LIMIT 1;
IF FOUND THEN
  IF checkdata THEN
      RAISE NOTICE 'update_adu has already been run for %%', updateday;
  END IF;
  RETURN FALSE;
END IF;

-- insert releases
-- note that we're now matching against product_guids were we can
-- and that we need to strip the {} out of the guids

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id
    , coalesce(os_name,'Unknown') as os
    , updateday
    , coalesce(sum(adu_count), 0)
FROM product_versions
    LEFT OUTER JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            os_name_matches.os_name
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.version_string = prod_adu.product_version
        AND product_versions.build_type = prod_adu.build_channel
WHERE product_versions.build_type IN ('release','nightly','aurora')
    AND product_versions.build_date >= ( current_date - interval '2 years' )
GROUP BY product_version_id, os;

-- insert ESRs
-- need a separate query here because the ESR version number doesn't match

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id
    , coalesce(os_name,'Unknown') as os
    , updateday
    , coalesce(sum(adu_count), 0)
FROM product_versions
    LEFT OUTER JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            os_name_matches.os_name
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
            and raw_adu.build_channel = 'esr'
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.version_string
            =  ( prod_adu.product_version || 'esr' )
        AND product_versions.build_type = prod_adu.build_channel
WHERE product_versions.build_type = 'ESR'
    AND product_versions.build_date >= ( current_date - interval '2 years' )
GROUP BY product_version_id, os;

-- insert betas

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id
    , coalesce(os_name,'Unknown') as os
    , updateday
    , coalesce(sum(adu_count), 0)
FROM product_versions
    JOIN products USING ( product_name )
    LEFT OUTER JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            os_name_matches.os_name,
            build_numeric(raw_adu.build) as build_id
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
            AND raw_adu.build_channel = 'beta'
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.release_version = prod_adu.product_version
        AND product_versions.build_type = prod_adu.build_channel
WHERE product_versions.build_type = 'Beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = prod_adu.build_id
            )
      AND product_versions.build_date >= ( current_date - interval '2 years' )
GROUP BY product_version_id, os;


RETURN TRUE;
END; $$
"""
	connection.execute(update_adu)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_build_adu(target, connection, **kw):
	update_build_adu = """
CREATE FUNCTION update_build_adu(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM build_adu
    WHERE adu_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'build_adu has already been run for %%.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if raw_adu is available
PERFORM 1 FROM raw_adu
WHERE "date" = updateday
LIMIT 1;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE EXCEPTION 'raw_adu has not been updated for %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- insert nightly, aurora
-- only 7 days of data after each build

INSERT INTO build_adu ( product_version_id, os_name,
        adu_date, build_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    bdate,
    coalesce(sum(adu_count), 0)
FROM product_versions
    JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            build_date(build_numeric(raw_adu.build)) as bdate,
            os_name_matches.os_name
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.version_string = prod_adu.product_version
        AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type IN ('nightly','aurora')
        AND bdate is not null
        AND updateday <= ( bdate + 6 )
GROUP BY product_version_id, os, bdate;

-- insert betas
-- rapid beta parent entries only
-- only 7 days of data after each build

INSERT INTO build_adu ( product_version_id, os_name,
        adu_date, build_date, adu_count )
SELECT rapid_beta_id, coalesce(os_name,'Unknown') as os,
    updateday,
    bdate,
    coalesce(sum(adu_count), 0)
FROM product_versions
    JOIN products USING ( product_name )
    JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            os_name_matches.os_name,
            build_numeric(raw_adu.build) as build_id,
            build_date(build_numeric(raw_adu.build)) as bdate
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
            AND raw_adu.build_channel = 'beta'
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.release_version = prod_adu.product_version
        AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'Beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = prod_adu.build_id
            )
        AND bdate is not null
        AND rapid_beta_id IS NOT NULL
        AND updateday <= ( bdate + 6 )
GROUP BY rapid_beta_id, os, bdate;

RETURN TRUE;
END; $$
"""
	connection.execute(update_build_adu)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_correlations(target, connection, **kw):
	update_correlations = """
CREATE FUNCTION update_correlations(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates daily matviews
-- for some of the correlation reports
-- depends on reports_clean

-- no need to check if we've been run, since the correlations
-- only hold the last day of data

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- clear the correlations list
-- can't use TRUNCATE here because of locking
DELETE FROM correlations;

--create the correlations list
INSERT INTO correlations ( signature_id, product_version_id,
	os_name, reason_id, crash_count )
SELECT signature_id, product_version_id,
	os_name, reason_id, count(*)
FROM reports_clean
	JOIN product_versions USING ( product_version_id )
WHERE updateday BETWEEN build_date and sunset_date
	and utc_day_is(date_processed, updateday)
GROUP BY product_version_id, os_name, reason_id, signature_id
ORDER BY product_version_id, os_name, reason_id, signature_id;

ANALYZE correlations;

-- create list of UUID-report_id correspondences for the day
CREATE TEMPORARY TABLE uuid_repid
AS
SELECT uuid, id as report_id
FROM reports
WHERE utc_day_is(date_processed, updateday)
ORDER BY uuid, report_id;
CREATE INDEX uuid_repid_key on uuid_repid(uuid, report_id);
ANALYZE uuid_repid;

--create the correlation-addons list
INSERT INTO correlation_addons (
	correlation_id, addon_key, addon_version, crash_count )
SELECT correlation_id, extension_id, extension_version, count(*)
FROM correlations
	JOIN reports_clean
		USING ( product_version_id, os_name, reason_id, signature_id )
	JOIN uuid_repid
		USING ( uuid )
	JOIN extensions
		USING ( report_id )
	JOIN product_versions
		USING ( product_version_id )
WHERE utc_day_is(reports_clean.date_processed, updateday)
	AND utc_day_is(extensions.date_processed, updateday)
	AND updateday BETWEEN build_date AND sunset_date
GROUP BY correlation_id, extension_id, extension_version;

ANALYZE correlation_addons;

--create correlations-cores list
INSERT INTO correlation_cores (
	correlation_id, architecture, cores, crash_count )
SELECT correlation_id, architecture, cores, count(*)
FROM correlations
	JOIN reports_clean
		USING ( product_version_id, os_name, reason_id, signature_id )
	JOIN product_versions
		USING ( product_version_id )
WHERE utc_day_is(reports_clean.date_processed, updateday)
	AND updateday BETWEEN build_date AND sunset_date
	AND architecture <> '' AND cores >= 0
GROUP BY correlation_id, architecture, cores;

ANALYZE correlation_cores;

RETURN TRUE;
END; $$
"""
	connection.execute(update_correlations)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_crashes_by_user(target, connection, **kw):
	update_crashes_by_user = """
CREATE FUNCTION update_crashes_by_user(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN
-- this function populates a daily matview
-- for general statistics of crashes by user
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM crashes_by_user
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'crashes_by_user has already been run for %%.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM product_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'product_adu has not been updated for %%', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
INSERT INTO crashes_by_user
    ( product_version_id, report_date,
      report_count, adu,
      os_short_name, crash_type_id )
SELECT product_version_id
    , updateday
    , coalesce(report_count,0)
    , coalesce(adu_sum, 0)
    , os_short_name
    , crash_type_id
FROM ( select product_versions.product_version_id,
            count(reports_clean.uuid) as report_count,
            os_names.os_name, os_short_name, crash_type_id
      FROM product_versions
        CROSS JOIN crash_types
        CROSS JOIN os_names
        LEFT OUTER JOIN reports_clean ON
            product_versions.product_version_id = reports_clean.product_version_id
            and utc_day_is(date_processed, updateday)
            AND reports_clean.process_type = crash_types.process_type
            AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
            AND reports_clean.os_name = os_names.os_name
      WHERE product_versions.build_date >= ( current_date - interval '2 years' )
      GROUP BY product_versions.product_version_id,
        os_names.os_name, os_short_name, crash_type_id
        ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name
        from product_adu
        where adu_date = updateday
        group by product_version_id, os_name ) as sum_adu
      USING ( product_version_id, os_name )
ORDER BY product_version_id;

-- insert records for the rapid beta parent entries
INSERT INTO crashes_by_user
    ( product_version_id, report_date,
      report_count, adu,
      os_short_name, crash_type_id )
SELECT product_versions.rapid_beta_id
    , updateday
    , sum(report_count)
    , sum(adu)
    , os_short_name
    , crash_type_id
FROM crashes_by_user
    JOIN product_versions USING ( product_version_id )
WHERE rapid_beta_id IS NOT NULL
    AND report_date = updateday
GROUP BY rapid_beta_id, os_short_name, crash_type_id;

RETURN TRUE;
END; $$
"""
	connection.execute(update_crashes_by_user)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_crashes_by_user_build(target, connection, **kw):
	update_crashes_by_user_build = """
CREATE FUNCTION update_crashes_by_user_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN
-- this function populates a daily matview
-- for general statistics of crashes by user
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM crashes_by_user_build
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'crashes_by_user_build has already been run for %%.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM build_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'build_adu has not been updated for %%', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
-- first, nightly and aurora are fairly straightforwards

INSERT INTO crashes_by_user_build
    ( product_version_id, report_date,
      build_date, report_count, adu,
      os_short_name, crash_type_id )
SELECT product_version_id, updateday,
    count_reports.build_date, report_count, adu_sum,
    os_short_name, crash_type_id
FROM ( select product_versions.product_version_id,
            count(DISTINCT reports_clean.uuid) as report_count,
            os_names.os_name, os_short_name, crash_type_id,
            build_date(build_id) as build_date
      FROM product_versions
      	JOIN product_version_builds USING (product_version_id)
      	CROSS JOIN crash_types
      	CROSS JOIN os_names
      	LEFT OUTER JOIN reports_clean ON
      		product_versions.product_version_id = reports_clean.product_version_id
      		and utc_day_is(date_processed, updateday)
      		AND reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      		AND reports_clean.os_name = os_names.os_name
      		AND reports_clean.release_channel IN ('nightly','aurora')
      		AND product_version_builds.build_id = reports_clean.build
      WHERE
          -- only accumulate data for each build for 7 days after build
          updateday <= ( build_date(build_id) + 6 )
      GROUP BY product_versions.product_version_id, os_names.os_name, os_short_name, crash_type_id,
      	build_date(build_id)
    ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name, build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, os_name, build_date ) as sum_adu
      USING ( product_version_id, os_name, build_date )
      JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;

-- rapid beta needs to be inserted with the productid of the
-- parent beta product_version instead of its
-- own product_version_id.

INSERT INTO crashes_by_user_build
    ( product_version_id, report_date,
      build_date, report_count, adu,
      os_short_name, crash_type_id )
SELECT rapid_beta_id, updateday,
    count_reports.build_date, report_count, adu_sum,
    os_short_name, crash_type_id
FROM ( select rapid_beta_id AS product_version_id,
            count(distinct reports_clean.uuid) as report_count,
            os_names.os_name, os_short_name, crash_type_id,
            build_date(build_id) as build_date
      FROM product_versions
        JOIN product_version_builds USING (product_version_id)
      	CROSS JOIN crash_types
      	CROSS JOIN os_names
      	LEFT OUTER JOIN reports_clean ON
      		product_versions.product_version_id = reports_clean.product_version_id
      		and utc_day_is(date_processed, updateday)
      		AND reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      		AND reports_clean.os_name = os_names.os_name
      		AND reports_clean.release_channel = 'beta'
      		AND reports_clean.build = product_version_builds.build_id
      WHERE
          -- only accumulate data for each build for 7 days after build
          updateday <= ( build_date(build_id) + 6 )
          AND product_versions.rapid_beta_id IS NOT NULL
      GROUP BY rapid_beta_id, os_names.os_name, os_short_name, crash_type_id,
      	build_date(build_id)
      	) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name, build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, os_name, build_date ) as sum_adu
      USING ( product_version_id, os_name, build_date )
      JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;


RETURN TRUE;
END; $$
"""
	connection.execute(update_crashes_by_user_build)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_daily_crashes(target, connection, **kw):
	update_daily_crashes = """
CREATE FUNCTION update_daily_crashes(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN
-- update the daily crashes summary matview
-- VERSION 4
-- updates daily_crashes for new products using reports_clean
-- instead of using reports

-- apologies for badly written SQL, didn't want to rewrite it all from scratch

-- note: we are currently excluding crashes which are missing an OS_Name from the count

-- check if we've already been run
IF checkdata THEN
	PERFORM 1 FROM daily_crashes
	WHERE adu_day = updateday LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'daily_crashes has already been run for %%', updateday;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- insert old browser crashes
-- for most crashes
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code, p.id,
	substring(r.os_name, 1, 3) AS os_short_name,
	updateday
FROM product_visibility cfg
JOIN productdims p on cfg.productdims_id = p.id
JOIN reports r on p.product = r.product AND p.version = r.version
WHERE NOT cfg.ignore AND
	date_processed >= ( updateday::timestamptz )
		AND date_processed < ( updateday + 1 )::timestamptz
	AND updateday BETWEEN cfg.start_date and cfg.end_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
GROUP BY p.id, crash_code, os_short_name;

 -- insert HANGS_NORMALIZED from old data
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name
		   FROM product_visibility cfg
		   JOIN productdims p on cfg.productdims_id = p.id
		   JOIN reports r on p.product = r.product AND p.version = r.version
		   WHERE NOT cfg.ignore AND
			date_processed >= ( updateday::timestamptz )
				AND date_processed < ( updateday + 1 )::timestamptz
				AND updateday BETWEEN cfg.start_date and cfg.end_date
				AND hangid IS NOT NULL
                AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

-- insert crash counts for new products
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hang_id) as crash_code,
	product_version_id,
	initcap(os_short_name),
	updateday
FROM reports_clean JOIN product_versions USING (product_version_id)
	JOIN os_names USING (os_name)
WHERE utc_day_is(date_processed, updateday)
	AND updateday BETWEEN product_versions.build_date and sunset_date
GROUP BY product_version_id, crash_code, os_short_name;

-- insert normalized hangs for new products
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(DISTINCT hang_id) as count, 'H',
	product_version_id, initcap(os_short_name),
	updateday
FROM product_versions
	JOIN reports_clean USING ( product_version_id )
	JOIN os_names USING (os_name)
	WHERE utc_day_is(date_processed, updateday)
		AND updateday BETWEEN product_versions.build_date and sunset_date
GROUP BY product_version_id, os_short_name;

ANALYZE daily_crashes;

RETURN TRUE;

END;$$
"""
	connection.execute(update_daily_crashes)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_explosiveness(target, connection, **kw):
	update_explosiveness = """
CREATE FUNCTION update_explosiveness(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
-- set stats parameters per Kairo
DECLARE
	-- minimum crashes/mil.adu to show up
	minrate INT := 10;
	-- minimum comparitor figures if there are no
	-- or very few proir crashes to smooth curves
	-- mostly corresponds to Kairo "clampperadu"
	mindiv_one INT := 30;
	mindiv_three INT := 15;
	mes_edate DATE;
	mes_b3date DATE;
	comp_e1date DATE;
	comp_e3date DATE;
	comp_bdate DATE;
BEGIN
-- this function populates a daily matview
-- for explosiveness
-- depends on tcbs and product_adu

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM explosiveness
	WHERE last_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE INFO 'explosiveness has already been run for %%.',updateday;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check if product_adu and tcbs are updated
PERFORM 1
FROM tcbs JOIN product_adu
   ON tcbs.report_date = product_adu.adu_date
WHERE tcbs.report_date = updateday
LIMIT 1;

IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Either product_adu or tcbs have not been updated to the end of %%',updateday;
	ELSE
		RAISE NOTICE 'Either product_adu or tcbs has not been updated, skipping.';
		RETURN TRUE;
	END IF;
END IF;

-- compute dates
-- note that dates are inclusive
-- last date of measured period
mes_edate := updateday;
-- first date of the measured period for 3-day
mes_b3date := updateday - 2;
-- last date of the comparison period for 1-day
comp_e1date := updateday - 1;
-- last date of the comparison period for 3-day
comp_e3date := mes_b3date - 1;
-- first date of the comparison period
comp_bdate := mes_edate - 9;

-- create temp table with all of the crash_madus for each
-- day, including zeroes
CREATE TEMPORARY TABLE crash_madu
ON COMMIT DROP
AS
WITH crashdates AS (
	SELECT report_date::DATE as report_date
	FROM generate_series(comp_bdate, mes_edate, INTERVAL '1 day')
		AS gs(report_date)
),
adusum AS (
	SELECT adu_date, sum(adu_count) as adu_count,
		( mindiv_one * 1000000::numeric / sum(adu_count)) as mindivisor,
		product_version_id
	FROM product_adu
	WHERE adu_date BETWEEN comp_bdate and mes_edate
		AND adu_count > 0
	GROUP BY adu_date, product_version_id
),
reportsum AS (
	SELECT report_date, sum(report_count) as report_count,
		product_version_id, signature_id
	FROM tcbs
	WHERE report_date BETWEEN comp_bdate and mes_edate
	GROUP BY report_date, product_version_id, signature_id
),
crash_madu_raw AS (
	SELECT ( report_count * 1000000::numeric ) / adu_count AS crash_madu,
		reportsum.product_version_id, reportsum.signature_id,
		report_date, mindivisor
	FROM adusum JOIN reportsum
		ON adu_date = report_date
		AND adusum.product_version_id = reportsum.product_version_id
),
product_sigs AS (
	SELECT DISTINCT product_version_id, signature_id
	FROM crash_madu_raw
)
SELECT crashdates.report_date,
	coalesce(crash_madu, 0) as crash_madu,
	product_sigs.product_version_id, product_sigs.signature_id,
	COALESCE(crash_madu_raw.mindivisor, 0) as mindivisor
FROM crashdates CROSS JOIN product_sigs
	LEFT OUTER JOIN crash_madu_raw
	ON crashdates.report_date = crash_madu_raw.report_date
		AND product_sigs.product_version_id = crash_madu_raw.product_version_id
		AND product_sigs.signature_id = crash_madu_raw.signature_id;

-- create crosstab with days1-10
-- create the multiplier table

CREATE TEMPORARY TABLE xtab_mult
ON COMMIT DROP
AS
SELECT report_date,
	( case when report_date = mes_edate THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day0,
	( case when report_date = ( mes_edate - 1 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day1,
	( case when report_date = ( mes_edate - 2 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day2,
	( case when report_date = ( mes_edate - 3 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day3,
	( case when report_date = ( mes_edate - 4 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day4,
	( case when report_date = ( mes_edate - 5 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day5,
	( case when report_date = ( mes_edate - 6 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day6,
	( case when report_date = ( mes_edate - 7 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day7,
	( case when report_date = ( mes_edate - 8 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day8,
	( case when report_date = ( mes_edate - 9 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day9
	FROM generate_series(comp_bdate, mes_edate, INTERVAL '1 day')
		AS gs(report_date);

-- create the crosstab
CREATE TEMPORARY TABLE crash_xtab
ON COMMIT DROP
AS
SELECT product_version_id, signature_id,
	round(SUM ( crash_madu * day0 ),2) AS day0,
	round(SUM ( crash_madu * day1 ),2) AS day1,
	round(SUM ( crash_madu * day2 ),2) AS day2,
	round(SUM ( crash_madu * day3 ),2) AS day3,
	round(SUM ( crash_madu * day4 ),2) AS day4,
	round(SUM ( crash_madu * day5 ),2) AS day5,
	round(SUM ( crash_madu * day6 ),2) AS day6,
	round(SUM ( crash_madu * day7 ),2) AS day7,
	round(SUM ( crash_madu * day8 ),2) AS day8,
	round(SUM ( crash_madu * day9 ),2) AS day9
FROM xtab_mult
	JOIN crash_madu USING (report_date)
GROUP BY product_version_id, signature_id;

-- create oneday temp table
CREATE TEMPORARY TABLE explosive_oneday
ON COMMIT DROP
AS
WITH sum1day AS (
	SELECT product_version_id, signature_id, crash_madu as sum1day,
		mindivisor
	FROM crash_madu
	WHERE report_date = mes_edate
	AND crash_madu > 10
),
agg9day AS (
	SELECT product_version_id, signature_id,
		AVG(crash_madu) AS avg9day,
		MAX(crash_madu) as max9day
	FROM crash_madu
	WHERE report_date BETWEEN comp_bdate and comp_e1date
	GROUP BY product_version_id, signature_id
)
SELECT sum1day.signature_id,
	sum1day.product_version_id ,
	round (
		( sum1day.sum1day - coalesce(agg9day.avg9day,0) )
			/
		GREATEST ( agg9day.max9day - agg9day.avg9day, sum1day.mindivisor )
		, 2 )
	as explosive_1day,
	round(sum1day,2) as oneday_rate
FROM sum1day
	LEFT OUTER JOIN agg9day USING ( signature_id, product_version_id )
WHERE sum1day.sum1day IS NOT NULL;

ANALYZE explosive_oneday;

-- create threeday temp table
CREATE TEMPORARY TABLE explosive_threeday
ON COMMIT DROP
AS
WITH avg3day AS (
	SELECT product_version_id, signature_id,
        AVG(crash_madu) as avg3day,
		AVG(mindivisor) as mindivisor
	FROM crash_madu
	WHERE report_date BETWEEN mes_b3date and mes_edate
	GROUP BY product_version_id, signature_id
	HAVING AVG(crash_madu) > 10
),
agg7day AS (
	SELECT product_version_id, signature_id,
		SUM(crash_madu)/7 AS avg7day,
		COALESCE(STDDEV(crash_madu),0) AS sdv7day
	FROM crash_madu
	WHERE report_date BETWEEN comp_bdate and comp_e3date
	GROUP BY product_version_id, signature_id
)
SELECT avg3day.signature_id,
	avg3day.product_version_id ,
	round (
		( avg3day - coalesce(avg7day,0) )
			/
		GREATEST ( sdv7day, avg3day.mindivisor )
		, 2 )
	as explosive_3day,
	round(avg3day, 2) as threeday_rate
FROM avg3day LEFT OUTER JOIN agg7day
	USING ( signature_id, product_version_id );

ANALYZE explosive_threeday;

-- truncate explosiveness
DELETE FROM explosiveness;

-- merge the two tables and insert
INSERT INTO explosiveness (
	last_date, signature_id, product_version_id,
	oneday, threeday,
	day0, day1, day2, day3, day4,
	day5, day6, day7, day8, day9)
SELECT updateday, signature_id, product_version_id,
	explosive_1day, explosive_3day,
	day0, day1, day2, day3, day4,
	day5, day6, day7, day8, day9
FROM crash_xtab
	LEFT OUTER JOIN explosive_oneday
	USING ( signature_id, product_version_id )
	LEFT OUTER JOIN explosive_threeday
	USING ( signature_id, product_version_id )
WHERE explosive_1day IS NOT NULL or explosive_3day IS NOT NULL
ORDER BY product_version_id;

RETURN TRUE;
END; $$
"""
	connection.execute(update_explosiveness)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_final_betas(target, connection, **kw):
	update_final_betas = """
CREATE FUNCTION update_final_betas(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
	RETURN TRUE;
END; $$
"""
	connection.execute(update_final_betas)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_hang_report(target, connection, **kw):
	update_hang_report = """
CREATE FUNCTION update_hang_report(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    AS $$
BEGIN

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check if we already have hang data
PERFORM 1 FROM daily_hangs
WHERE report_date = updateday LIMIT 1;
IF FOUND THEN
	RAISE EXCEPTION 'it appears that hang_report has already been run for %%.  If you are backfilling, use backfill_hang_report instead.',updateday;
END IF;

-- insert data
-- note that we need to group on the plugin here and
-- take min() of all of the browser crash data.  this is a sloppy
-- approach but works because the only reason for more than one
-- browser crash in a hang group is duplicate crash data
INSERT INTO daily_hangs ( uuid, plugin_uuid, report_date,
	product_version_id, browser_signature_id, plugin_signature_id,
	hang_id, flash_version_id, duplicates, url )
SELECT
    min(browser.uuid) ,
    plugin.uuid,
    updateday as report_date,
    min(browser.product_version_id),
    min(browser.signature_id),
    plugin.signature_id AS plugin_signature_id,
    plugin.hang_id,
    plugin.flash_version_id,
    nullif(array_agg(browser.duplicate_of)
    	|| COALESCE(ARRAY[plugin.duplicate_of], '{}'),'{NULL}'),
    min(browser_info.url)
FROM reports_clean AS browser
    JOIN reports_clean AS plugin ON plugin.hang_id = browser.hang_id
    LEFT OUTER JOIN reports_user_info AS browser_info ON browser.uuid = browser_info.uuid
    JOIN signatures AS sig_browser
        ON sig_browser.signature_id = browser.signature_id
WHERE sig_browser.signature LIKE 'hang | %%'
    AND browser.hang_id != ''
    AND browser.process_type = 'browser'
    AND plugin.process_type = 'plugin'
    AND utc_day_near(browser.date_processed, updateday)
    AND utc_day_is(plugin.date_processed, updateday)
    AND utc_day_is(browser_info.date_processed, updateday)
GROUP BY plugin.uuid, plugin.signature_id, plugin.hang_id, plugin.flash_version_id,
	plugin.duplicate_of;

ANALYZE daily_hangs;
RETURN TRUE;
END;$$
"""
	connection.execute(update_hang_report)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_home_page_graph(target, connection, **kw):
	update_home_page_graph = """
CREATE FUNCTION update_home_page_graph(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM home_page_graph
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'home_page_graph has already been run for %%.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM product_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'product_adu has not been updated for %%', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
INSERT INTO home_page_graph
    ( product_version_id, report_date,
      report_count, adu, crash_hadu )
SELECT product_version_id, updateday,
    report_count, adu_sum,
    crash_hadu(report_count, adu_sum, throttle)
FROM ( select product_version_id,
            count(*) as report_count
      from reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          AND updateday BETWEEN build_date AND sunset_date
      group by product_version_id ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum
        from product_adu
        where adu_date = updateday
        group by product_version_id ) as sum_adu
      USING ( product_version_id )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
WHERE sunset_date > ( current_date - interval '1 year' )
ORDER BY product_version_id;

-- insert summary records for rapid_beta parents
INSERT INTO home_page_graph
    ( product_version_id, report_date,
      report_count, adu, crash_hadu )
SELECT rapid_beta_id, updateday,
    sum(report_count), sum(adu),
    crash_hadu(sum(report_count), sum(adu))
FROM home_page_graph
	JOIN product_versions USING ( product_version_id )
WHERE rapid_beta_id IS NOT NULL
	AND report_date = updateday
GROUP BY rapid_beta_id, updateday;

RETURN TRUE;
END; $$
"""
	connection.execute(update_home_page_graph)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_home_page_graph_build(target, connection, **kw):
	update_home_page_graph_build = """
CREATE FUNCTION update_home_page_graph_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM home_page_graph_build
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'home_page_graph_build has already been run for %%.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM build_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'build_adu has not been updated for %%', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records for nightly and aurora

INSERT INTO home_page_graph_build
    ( product_version_id, build_date, report_date,
      report_count, adu )
SELECT product_version_id, count_reports.build_date, updateday,
    report_count, adu_sum
FROM ( select product_version_id,
            count(*) as report_count,
            build_date(build) as build_date
      FROM reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- only 7 days of each build
          AND build_date(build) >= ( updateday - 6 )
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          -- only visible products
          AND updateday BETWEEN product_versions.build_date AND product_versions.sunset_date
          -- aurora, nightly, and rapid beta only
          AND reports_clean.release_channel IN ( 'nightly','aurora' )
      group by product_version_id, build_date(build) ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, build_date ) as sum_adu
      USING ( product_version_id, build_date )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
ORDER BY product_version_id;

-- insert records for the "parent" rapid beta

INSERT INTO home_page_graph_build
    ( product_version_id, build_date, report_date,
      report_count, adu )
SELECT product_version_id, count_reports.build_date, updateday,
    report_count, adu_sum
FROM ( select rapid_beta_id AS product_version_id,
            count(*) as report_count,
            build_date(build) as build_date
      FROM reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- only 7 days of each build
          AND build_date(build) >= ( updateday - 6 )
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          -- only visible products
          AND updateday BETWEEN product_versions.build_date AND product_versions.sunset_date
          -- aurora, nightly, and rapid beta only
          AND reports_clean.release_channel = 'beta'
          AND rapid_beta_id IS NOT NULL
      group by rapid_beta_id, build_date(build) ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, build_date ) as sum_adu
      USING ( product_version_id, build_date )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
ORDER BY product_version_id;


RETURN TRUE;
END; $$
"""
	connection.execute(update_home_page_graph_build)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_lookup_new_reports(target, connection, **kw):
	update_lookup_new_reports = """
CREATE FUNCTION update_lookup_new_reports(column_name text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare table_name text;
	insert_query text;
begin
	IF column_name LIKE '%%s' THEN
		table_name := column_name || 'es';
	ELSE
		table_name := column_name || 's';
	END IF;
	
	insert_query := '
		insert into ' || table_name || ' ( ' || column_name || ', first_seen )
		select newrecords.* from ( 
			select ' || column_name || '::citext as col,
				min(date_processed) as first_report
			from new_reports
			group by col ) as newrecords
		left join ' || table_name || ' as lookuplist
			on newrecords.col = lookuplist.' || column_name || '
		where lookuplist.' || column_name || ' IS NULL;';
	
	execute insert_query;
	
	RETURN true;
end; $$
"""
	connection.execute(update_lookup_new_reports)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_nightly_builds(target, connection, **kw):
	update_nightly_builds = """
CREATE FUNCTION update_nightly_builds(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM nightly_builds
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'nightly_builds has already been run for %%.',updateday;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- now insert the new records
-- this should be some appropriate query, this simple group by
-- is just provided as an example
INSERT INTO nightly_builds (
	product_version_id, build_date, report_date,
	days_out, report_count )
SELECT product_version_id,
	build_date(reports_clean.build) as build_date,
	date_processed::date as report_date,
	date_processed::date
		- build_date(reports_clean.build) as days_out,
	count(*)
FROM reports_clean
	join product_versions using (product_version_id)
	join product_version_builds using (product_version_id)
WHERE
	reports_clean.build = product_version_builds.build_id
	and reports_clean.release_channel IN ( 'nightly', 'aurora' )
	and date_processed::date
		- build_date(reports_clean.build) <= 14
	and tstz_between(date_processed, build_date, sunset_date)
	and utc_day_is(date_processed,updateday)
GROUP BY product_version_id, product_name, version_string,
	build_date(build), date_processed::date
ORDER BY product_version_id, build_date, days_out;

RETURN TRUE;
END; $$
"""
	connection.execute(update_nightly_builds)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_os_versions(target, connection, **kw):
	update_os_versions = """
CREATE FUNCTION update_os_versions(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET "TimeZone" TO 'UTC'
    AS $_$
BEGIN
-- function for daily batch update of os_version information
-- pulls new data out of reports
-- errors if no data found

create temporary table new_os
on commit drop as
select os_name, os_version
from reports
where date_processed >= updateday
	and date_processed <= ( updateday + 1 )
group by os_name, os_version;

PERFORM 1 FROM new_os LIMIT 1;
IF NOT FOUND THEN
	RAISE EXCEPTION 'No OS data found for date %%',updateday;
END IF;

create temporary table os_versions_temp
on commit drop as
select os_name_matches.os_name,
	substring(os_version from $x$^(\d+)$x$)::int as major_version,
	substring(os_version from $x$^\d+\.(\d+)$x$)::int as minor_version
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and substring(os_version from $x$^\d+\.(\d+)$x$)::numeric < 1000;

insert into os_versions_temp
select os_name_matches.os_name,
	substring(os_version from $x$^(\d+)$x$)::int,
	0
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and ( substring(os_version from $x$^\d+\.(\d+)$x$)::numeric >= 1000
		or os_version !~ $x$^\d+\.(\d+)$x$ );

insert into os_versions_temp
select os_name_matches.os_name,
	0,
	0
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version !~ $x$^\d+$x$
	or substring(os_version from $x$^(\d+)$x$)::numeric >= 1000
	or os_version is null;

insert into os_versions ( os_name, major_version, minor_version, os_version_string )
select os_name, major_version, minor_version,
	create_os_version_string( os_name, major_version, minor_version )
from (
select distinct os_name, major_version, minor_version
from os_versions_temp ) as os_rollup
left outer join os_versions
	USING ( os_name, major_version, minor_version )
where  os_versions.os_name is null;

RETURN true;
END; $_$
"""
	connection.execute(update_os_versions)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_os_versions_new_reports(target, connection, **kw):
	update_os_versions_new_reports = """
CREATE FUNCTION update_os_versions_new_reports() RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $_$
BEGIN
-- function for updating list of oses and versions
-- intended to be called internally by update_reports_clean.

create temporary table new_os
on commit drop as
select os_name, os_version
from new_reports
group by os_name, os_version;

create temporary table os_versions_temp
on commit drop as
select os_name_matches.os_name,
	substring(os_version from $x$^(\d+)$x$)::int as major_version,
	substring(os_version from $x$^\d+\.(\d+)$x$)::int as minor_version
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and substring(os_version from $x$^\d+\.(\d+)$x$)::numeric < 1000;

insert into os_versions_temp
select os_name_matches.os_name,
	substring(os_version from $x$^(\d+)$x$)::int,
	0
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and ( substring(os_version from $x$^\d+\.(\d+)$x$)::numeric >= 1000
		or os_version !~ $x$^\d+\.(\d+)$x$ );

insert into os_versions_temp
select os_name_matches.os_name,
	0,
	0
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version !~ $x$^\d+$x$
	or substring(os_version from $x$^(\d+)$x$)::numeric >= 1000
	or os_version is null;

insert into os_versions ( os_name, major_version, minor_version, os_version_string )
select os_name, major_version, minor_version,
	create_os_version_string( os_name, major_version, minor_version )
from (
select distinct os_name, major_version, minor_version
from os_versions_temp ) as os_rollup
left outer join os_versions
	USING ( os_name, major_version, minor_version )
where  os_versions.os_name is null;

drop table new_os;
drop table os_versions_temp;

RETURN true;
END; $_$
"""
	connection.execute(update_os_versions_new_reports)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_product_versions(target, connection, **kw):
	update_product_versions = """
CREATE FUNCTION update_product_versions(product_window integer DEFAULT 30) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    AS $$
BEGIN
-- daily batch update function for new products and versions
-- reads data from releases_raw, cleans it
-- and puts data corresponding to the new versions into
-- product_versions and related tables

-- is cumulative and can be run repeatedly without issues
-- now covers FennecAndroid and ESR releases
-- now only compares releases from the last 30 days
-- now restricts to only the canonical "repositories"
-- now covers webRT
-- now covers rapid betas, but no more final betas

-- create temporary table, required because
-- all of the special cases

create temporary table releases_recent
on commit drop
as
select COALESCE ( specials.product_name, products.product_name )
		AS product_name,
	releases_raw.version,
	releases_raw.beta_number,
	releases_raw.build_id,
	releases_raw.build_type,
	releases_raw.platform,
	( major_version_sort(version) >= major_version_sort(rapid_release_version) ) as is_rapid,
    is_rapid_beta(build_type, version, rapid_beta_version) as is_rapid_beta,
	releases_raw.repository
from releases_raw
	JOIN products ON releases_raw.product_name = products.release_name
	JOIN release_repositories ON releases_raw.repository = release_repositories.repository
	LEFT OUTER JOIN special_product_platforms AS specials
		ON releases_raw.platform::citext = specials.platform
		AND releases_raw.product_name = specials.release_name
		AND releases_raw.repository = specials.repository
		AND releases_raw.build_type = specials.release_channel
		AND major_version_sort(version) >= major_version_sort(min_version)
where build_date(build_id) > ( current_date - product_window )
	AND version_matches_channel(releases_raw.version, releases_raw.build_type);

--fix ESR versions

UPDATE releases_recent
SET build_type = 'ESR'
WHERE build_type ILIKE 'Release'
	AND version ILIKE '%%esr';

-- insert WebRT "releases", which are copies of Firefox releases
-- insert them only if the FF release is greater than the first
-- release for WebRT

INSERT INTO releases_recent
SELECT 'WebappRuntime',
	version, beta_number, build_id,
	build_type, platform,
	is_rapid, is_rapid_beta, repository
FROM releases_recent
	JOIN products
		ON products.product_name = 'WebappRuntime'
WHERE releases_recent.product_name = 'Firefox'
	AND major_version_sort(releases_recent.version)
		>= major_version_sort(products.rapid_release_version);

-- now put it in product_versions
-- first releases, aurora and nightly and non-rapid betas

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    has_builds )
select releases_recent.product_name,
	to_major_version(version),
	version,
	version_string(version, releases_recent.beta_number),
	releases_recent.beta_number,
	version_sort(version, releases_recent.beta_number),
	build_date(min(build_id)),
	sunset_date(min(build_id), releases_recent.build_type ),
	releases_recent.build_type::citext,
	( releases_recent.build_type IN ('aurora', 'nightly') )
from releases_recent
	left outer join product_versions ON
		( releases_recent.product_name = product_versions.product_name
			AND releases_recent.version = product_versions.release_version
			AND releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
where is_rapid
    AND product_versions.product_name IS NULL
    AND NOT releases_recent.is_rapid_beta
group by releases_recent.product_name, version,
	releases_recent.beta_number,
	releases_recent.build_type::citext;

-- insert rapid betas "parent" products
-- these will have a product, but no builds

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    is_rapid_beta,
    has_builds )
select products.product_name,
    to_major_version(version),
    version,
    version || 'b',
    0,
    version_sort(version, 0),
    build_date(min(build_id)),
    sunset_date(min(build_id), 'beta' ),
    'beta',
    TRUE,
    TRUE
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = 0 )
where is_rapid
    and releases_recent.is_rapid_beta
    and product_versions.product_name IS NULL
group by products.product_name, version;

-- finally, add individual betas for rapid_betas
-- these need to get linked to their master rapid_beta

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    rapid_beta_id )
select products.product_name,
    to_major_version(version),
    version,
    version_string(version, releases_recent.beta_number),
    releases_recent.beta_number,
    version_sort(version, releases_recent.beta_number),
    build_date(min(build_id)),
    rapid_parent.sunset_date,
    'beta',
	rapid_parent.product_version_id
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = releases_recent.beta_number )
    join product_versions as rapid_parent ON
    	releases_recent.version = rapid_parent.release_version
    	and releases_recent.product_name = rapid_parent.product_name
    	and rapid_parent.is_rapid_beta
where is_rapid
    and releases_recent.is_rapid_beta
    and product_versions.product_name IS NULL
group by products.product_name, version, rapid_parent.product_version_id,
	releases_recent.beta_number, rapid_parent.sunset_date;

-- add build ids
-- note that rapid beta parent records will have no buildids of their own

insert into product_version_builds
select distinct product_versions.product_version_id,
		releases_recent.build_id,
		releases_recent.platform,
		releases_recent.repository
from releases_recent
	join product_versions
		ON releases_recent.product_name = product_versions.product_name
		AND releases_recent.version = product_versions.release_version
		AND releases_recent.build_type = product_versions.build_type
		AND ( releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
	left outer join product_version_builds ON
		product_versions.product_version_id = product_version_builds.product_version_id
		AND releases_recent.build_id = product_version_builds.build_id
		AND releases_recent.platform = product_version_builds.platform
where product_version_builds.product_version_id is null;

drop table releases_recent;

return true;
end; $$
"""
	connection.execute(update_product_versions)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_rank_compare(target, connection, **kw):
	update_rank_compare = """
CREATE FUNCTION update_rank_compare(updateday date DEFAULT NULL::date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates a daily matview
-- for rankings of signatures on TCBS
-- depends on the new reports_clean

-- run for yesterday if not set
updateday := COALESCE(updateday, ( CURRENT_DATE -1 ));

-- don't care if we've been run
-- since there's no historical data

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- obtain a lock on the matview so that we can TRUNCATE
IF NOT try_lock_table('rank_compare', 'ACCESS EXCLUSIVE') THEN
	RAISE EXCEPTION 'unable to lock the rank_compare table for update.';
END IF;

-- create temporary table with totals from reports_clean

CREATE TEMPORARY TABLE prod_sig_counts
AS SELECT product_version_id, signature_id, count(*) as report_count
FROM reports_clean
WHERE utc_day_is(date_processed, updateday)
GROUP BY product_version_id, signature_id;

-- truncate rank_compare since we don't need the old data

TRUNCATE rank_compare CASCADE;

-- now insert the new records
INSERT INTO rank_compare (
	product_version_id, signature_id,
	rank_days,
	report_count,
	total_reports,
	rank_report_count,
	percent_of_total)
SELECT product_version_id, signature_id,
	1,
	report_count,
	total_count,
	count_rank,
	round(( report_count::numeric / total_count ),5)
FROM (
	SELECT product_version_id, signature_id,
		report_count,
		sum(report_count) over (partition by product_version_id) as total_count,
		dense_rank() over (partition by product_version_id
							order by report_count desc) as count_rank
	FROM prod_sig_counts
) as initrank;

RETURN TRUE;
END; $$
"""
	connection.execute(update_rank_compare)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_reports_clean(target, connection, **kw):
	update_reports_clean = """
CREATE FUNCTION update_reports_clean(fromtime timestamp with time zone, fortime interval DEFAULT '01:00:00'::interval, checkdata boolean DEFAULT true, analyze_it boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET maintenance_work_mem TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $_$
declare rc_part TEXT;
	rui_part TEXT;
	newfortime INTERVAL;
begin
-- this function creates a reports_clean fact table and all associated dimensions
-- intended to be run hourly for a target time three hours ago or so
-- eventually to be replaced by code for the processors to run

-- VERSION: 7
-- now includes support for rapid betas, camino transition

-- accepts a timestamptz, so be careful that the calling script is sending
-- something appropriate

-- since we do allow dynamic timestamps, check if we split over a week
-- boundary.  if so, call self recursively for the first half of the period

IF ( week_begins_utc(fromtime) <>
	week_begins_utc( fromtime + fortime - interval '1 second' ) ) THEN
	PERFORM update_reports_clean( fromtime,
		( week_begins_utc( fromtime + fortime ) - fromtime ), checkdata );
	newfortime := ( fromtime + fortime ) - week_begins_utc( fromtime + fortime );
	fromtime := week_begins_utc( fromtime + fortime );
	fortime := newfortime;
END IF;

-- prevent calling for a period of more than one day

IF fortime > INTERVAL '1 day' THEN
	RAISE EXCEPTION 'you may not execute this function on more than one day of data';
END IF;

-- create a temporary table from the hour of reports you want to
-- process.  generally this will be from 3-4 hours ago to
-- avoid missing reports

-- RULE: replace NULL reason, address, flash_version, os_name with "Unknown"
-- RULE: replace NULL signature, url with ''
-- pre-cleaning: replace NULL product, version with ''
-- RULE: extract number of cores from cpu_info
-- RULE: convert all reference list TEXT values to CITEXT except Signature

create temporary table new_reports
on commit drop
as select uuid,
	date_processed,
	client_crash_date,
	uptime,
	install_age,
	build,
	COALESCE(signature, '')::text as signature,
	COALESCE(reason, 'Unknown')::citext as reason,
	COALESCE(address, 'Unknown')::citext as address,
	COALESCE(flash_version, 'Unknown')::citext as flash_version,
	COALESCE(product, '')::citext as product,
	COALESCE(version, '')::citext as version,
	COALESCE(os_name, 'Unknown')::citext as os_name,
	os_version::citext as os_version,
	coalesce(process_type, 'Browser') as process_type,
	COALESCE(url2domain(url),'') as domain,
	email, user_comments, url, app_notes,
	release_channel, hangid as hang_id,
	cpu_name as architecture,
	get_cores(cpu_info) as cores
from reports
where date_processed >= fromtime and date_processed < ( fromtime + fortime )
	and completed_datetime is not null;

-- check for no data

PERFORM 1 FROM new_reports
LIMIT 1;
IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'no report data found for period %%',fromtime;
	ELSE
		DROP TABLE new_reports;
		RETURN TRUE;
	END IF;
END IF;

create index new_reports_uuid on new_reports(uuid);
create index new_reports_signature on new_reports(signature);
create index new_reports_address on new_reports(address);
create index new_reports_domain on new_reports(domain);
create index new_reports_reason on new_reports(reason);
analyze new_reports;

-- trim reports_bad to 2 days of data
DELETE FROM reports_bad
WHERE date_processed < ( now() - interval '2 days' );

-- delete any reports which were already processed
delete from new_reports
using reports_clean
where new_reports.uuid = reports_clean.uuid
and reports_clean.date_processed between ( fromtime - interval '1 day' )
and ( fromtime + fortime + interval '1 day' );

-- RULE: strip leading "0.0.0 Linux" from Linux version strings
UPDATE new_reports
SET os_version = regexp_replace(os_version, $x$[0\.]+\s+Linux\s+$x$, '')
WHERE os_version LIKE '%%0.0.0%%'
	AND os_name ILIKE 'Linux%%';

-- RULE: IF camino, SET release_channel for camino 2.1
-- camino 2.2 will have release_channel properly set

UPDATE new_reports
SET release_channel = 'release'
WHERE product ilike 'camino'
	AND version like '2.1%%'
	AND version not like '%%pre%%';

UPDATE new_reports
SET release_channel = 'beta'
WHERE product ilike 'camino'
	AND version like '2.1%%'
	AND version like '%%pre%%';

-- insert signatures into signature list
insert into signatures ( signature, first_report, first_build )
select newsigs.* from (
	select signature::citext as signature,
		min(date_processed) as first_report,
		min(build_numeric(build)) as first_build
	from new_reports
	group by signature::citext ) as newsigs
left join signatures
	on newsigs.signature = signatures.signature
where signatures.signature IS NULL;

-- insert oses into os list

PERFORM update_os_versions_new_reports();

-- insert reasons into reason list

PERFORM update_lookup_new_reports('reason');

-- insert addresses into address list

PERFORM update_lookup_new_reports('address');

-- insert flash_versions into flash version list

PERFORM update_lookup_new_reports('flash_version');

-- insert domains into the domain list

PERFORM update_lookup_new_reports('domain');

-- do not update reports_duplicates
-- this procedure assumes that it has already been run
-- later reports_duplicates will become a callable function from this function
-- maybe

-- create empty reports_clean_buffer
create temporary table reports_clean_buffer
(
uuid text not null primary key,
date_processed timestamptz not null,
client_crash_date timestamptz,
product_version_id int,
build numeric,
signature_id int,
install_age interval,
uptime interval,
reason_id int,
address_id int,
os_name citext,
os_version_id int,
major_version int,
minor_version int,
hang_id text,
flash_version_id int,
process_type citext,
release_channel citext,
duplicate_of text,
domain_id int,
architecture citext,
cores int
) on commit drop ;

-- populate the new buffer with uuid, date_processed,
-- client_crash_date, build, install_time, uptime,
-- hang_id, duplicate_of, reason, address, flash_version,
-- release_channel

-- RULE: convert install_age, uptime to INTERVAL
-- RULE: convert reason, address, flash_version, URL domain to lookup list ID
-- RULE: add possible duplicate UUID link
-- RULE: convert release_channel to canonical release_channel based on
--	channel match list

INSERT INTO reports_clean_buffer
SELECT new_reports.uuid,
	new_reports.date_processed,
	client_crash_date,
	0,
	build_numeric(build),
	signatures.signature_id,
	install_age * interval '1 second',
	uptime * interval '1 second',
	reasons.reason_id,
	addresses.address_id,
	NULL, NULL, 0, 0,
	hang_id,
	flash_versions.flash_version_id,
	process_type,
	release_channel_matches.release_channel,
	reports_duplicates.duplicate_of,
	domains.domain_id,
	architecture,
	cores
FROM new_reports
LEFT OUTER JOIN release_channel_matches ON new_reports.release_channel ILIKE release_channel_matches.match_string
LEFT OUTER JOIN signatures ON new_reports.signature = signatures.signature
LEFT OUTER JOIN reasons ON new_reports.reason = reasons.reason
LEFT OUTER JOIN addresses ON new_reports.address = addresses.address
LEFT OUTER JOIN flash_versions ON new_reports.flash_version = flash_versions.flash_version
LEFT OUTER JOIN reports_duplicates ON new_reports.uuid = reports_duplicates.uuid
	AND reports_duplicates.date_processed BETWEEN (fromtime - interval '1 day') AND (fromtime + interval '1 day' )
LEFT OUTER JOIN domains ON new_reports.domain = domains.domain
ORDER BY new_reports.uuid;

ANALYZE reports_clean_buffer;

-- populate product_version

	-- RULE: populate releases/aurora/nightlies based on matching product name
	-- and version with release_version

UPDATE reports_clean_buffer
SET product_version_id = product_versions.product_version_id
FROM product_versions, new_reports
WHERE reports_clean_buffer.uuid = new_reports.uuid
	AND new_reports.product = product_versions.product_name
	AND new_reports.version = product_versions.release_version
	AND reports_clean_buffer.release_channel = product_versions.build_type
	AND reports_clean_buffer.release_channel <> 'beta';

	-- RULE: populate betas based on matching product_name, version with
	-- release_version, and build number.

UPDATE reports_clean_buffer
SET product_version_id = product_versions.product_version_id
FROM product_versions JOIN product_version_builds USING (product_version_id), new_reports
WHERE reports_clean_buffer.uuid = new_reports.uuid
	AND new_reports.product = product_versions.product_name
	AND new_reports.version = product_versions.release_version
	AND reports_clean_buffer.release_channel = product_versions.build_type
	AND reports_clean_buffer.build = product_version_builds.build_id
	AND reports_clean_buffer.release_channel = 'beta';

-- populate os_name and os_version

-- RULE: set os_name based on name matching strings

UPDATE reports_clean_buffer SET os_name = os_name_matches.os_name
FROM new_reports, os_name_matches
WHERE reports_clean_buffer.uuid = new_reports.uuid
	AND new_reports.os_name ILIKE os_name_matches.match_string;

-- RULE: if os_name isn't recognized, set major and minor versions to 0.
UPDATE reports_clean_buffer SET os_name = 'Unknown',
	major_version = 0, minor_version = 0
WHERE os_name IS NULL OR os_name NOT IN ( SELECT os_name FROM os_names );

-- RULE: set minor_version based on parsing the os_version string
-- for a second decimal between 0 and 1000 if os_name is not Unknown
UPDATE reports_clean_buffer
SET minor_version = substring(os_version from $x$^\d+\.(\d+)$x$)::int
FROM new_reports
WHERE new_reports.uuid = reports_clean_buffer.uuid
	and os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and substring(os_version from $x$^\d+\.(\d+)$x$)::numeric < 1000
	and reports_clean_buffer.os_name <> 'Unknown';

-- RULE: set major_version based on parsing the os_vesion string
-- for a number between 0 and 1000, but there's no minor version
UPDATE reports_clean_buffer
SET major_version = substring(os_version from $x$^(\d+)$x$)::int
FROM new_reports
WHERE new_reports.uuid = reports_clean_buffer.uuid
	AND os_version ~ $x$^\d+$x$
		and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
		and reports_clean_buffer.major_version = 0
		and reports_clean_buffer.os_name <> 'Unknown';

UPDATE reports_clean_buffer
SET os_version_id = os_versions.os_version_id
FROM os_versions
WHERE reports_clean_buffer.os_name = os_versions.os_name
	AND reports_clean_buffer.major_version = os_versions.major_version
	AND reports_clean_buffer.minor_version = os_versions.minor_version;

-- copy to reports_bad and delete bad reports
-- RULE: currently we purge reports which have any of the following
-- missing or invalid: product_version, release_channel, os_name

INSERT INTO reports_bad ( uuid, date_processed )
SELECT uuid, date_processed
FROM reports_clean_buffer
WHERE product_version_id = 0
	OR release_channel IS NULL
	OR signature_id IS NULL;

DELETE FROM reports_clean_buffer
WHERE product_version_id = 0
	OR release_channel IS NULL
	OR signature_id IS NULL;

-- check if the right reports_clean partition exists, or create it

rc_part := reports_clean_weekly_partition(fromtime, 'reports_clean');

-- check if the right reports_user_info partition exists, or create it

rui_part := reports_clean_weekly_partition(fromtime, 'reports_user_info');

-- copy to reports_clean

EXECUTE 'INSERT INTO ' || rc_part || '
	( uuid, date_processed, client_crash_date, product_version_id,
	  build, signature_id, install_age, uptime,
reason_id, address_id, os_name, os_version_id,
hang_id, flash_version_id, process_type, release_channel,
duplicate_of, domain_id, architecture, cores )
SELECT uuid, date_processed, client_crash_date, product_version_id,
	  build, signature_id, install_age, uptime,
reason_id, address_id, os_name, os_version_id,
hang_id, flash_version_id, process_type, release_channel,
duplicate_of, domain_id, architecture, cores
FROM reports_clean_buffer;';

IF analyze_it THEN
	EXECUTE 'ANALYZE ' || rc_part;
END IF;

-- copy to reports_user_info

EXECUTE 'INSERT INTO ' || rui_part || $$
	( uuid, date_processed, email, user_comments, url, app_notes )
SELECT new_reports.uuid, new_reports.date_processed,
		email, user_comments, url, app_notes
FROM new_reports JOIN reports_clean_buffer USING ( uuid )
WHERE email <> '' OR user_comments <> ''
	OR url <> '' OR app_notes <> '';$$;

EXECUTE 'ANALYZE ' || rui_part;

-- exit
DROP TABLE new_reports;
DROP TABLE reports_clean_buffer;
RETURN TRUE;

END;
$_$
"""
	connection.execute(update_reports_clean)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_reports_clean_cron(target, connection, **kw):
	update_reports_clean_cron = """
CREATE FUNCTION update_reports_clean_cron(crontime timestamp with time zone) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT update_reports_clean( date_trunc('hour', $1) - interval '1 hour' );
$_$
"""
	connection.execute(update_reports_clean_cron)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_reports_duplicates(target, connection, **kw):
	update_reports_duplicates = """
CREATE FUNCTION update_reports_duplicates(start_time timestamp with time zone, end_time timestamp with time zone) RETURNS integer
    LANGUAGE plpgsql
    SET work_mem TO '256MB'
    SET temp_buffers TO '128MB'
    AS $$
declare new_dups INT;
begin

-- create a temporary table with the new duplicates
-- for the hour
-- this query contains the duplicate-finding algorithm
-- so it will probably change frequently

create temporary table new_reports_duplicates
on commit drop
as
select follower.uuid as uuid,
	leader.uuid as duplicate_of,
	follower.date_processed
from
(
select uuid,
    install_age,
    uptime,
    client_crash_date,
    date_processed,
  first_value(uuid)
  over ( partition by
            product,
            version,
            build,
            signature,
            cpu_name,
            cpu_info,
            os_name,
            os_version,
            address,
            topmost_filenames,
            reason,
            app_notes,
            url
         order by
            client_crash_date,
            uuid
        ) as leader_uuid
   from reports
   where date_processed BETWEEN start_time AND end_time
 ) as follower
JOIN
  ( select uuid, install_age, uptime, client_crash_date
    FROM reports
    where date_processed BETWEEN start_time AND end_time ) as leader
  ON follower.leader_uuid = leader.uuid
WHERE ( same_time_fuzzy(leader.client_crash_date, follower.client_crash_date,
                  leader.uptime, follower.uptime)
		  OR follower.uptime < 60
  	  )
  AND
	same_time_fuzzy(leader.client_crash_date, follower.client_crash_date,
                  leader.install_age, follower.install_age)
  AND follower.uuid <> leader.uuid;

-- insert a copy of the leaders

insert into new_reports_duplicates
select uuid, uuid, date_processed
from reports
where uuid IN ( select duplicate_of
	from new_reports_duplicates )
	and date_processed BETWEEN start_time AND end_time;

analyze new_reports_duplicates;

select count(*) into new_dups from new_reports_duplicates;

-- insert new duplicates into permanent table

insert into reports_duplicates (uuid, duplicate_of, date_processed )
select new_reports_duplicates.*
from new_reports_duplicates
	left outer join reports_duplicates 
		ON new_reports_duplicates.uuid = reports_duplicates.uuid
		AND reports_duplicates.date_processed > ( start_time - INTERVAL '1 day' )
		AND reports_duplicates.date_processed < ( end_time + INTERVAL '1 day' )
where reports_duplicates.uuid IS NULL;

-- done return number of dups found and exit
DROP TABLE new_reports_duplicates;
RETURN new_dups;
end;$$
"""
	connection.execute(update_reports_duplicates)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_signatures(target, connection, **kw):
	update_signatures = """
CREATE FUNCTION update_signatures(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN

-- new function for updating signature information post-rapid-release
-- designed to be run once per UTC day.
-- running it repeatedly won't cause issues
-- combines NULL and empty signatures

-- create temporary table

create temporary table new_signatures
on commit drop as
select coalesce(signature,'') as signature,
	product::citext as product,
	version::citext as version,
	build, NULL::INT as product_version_id,
	min(date_processed) as first_report
from reports
where date_processed >= updateday
	and date_processed <= (updateday + 1)
group by signature, product, version, build;

PERFORM 1 FROM new_signatures;
IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'no signature data found in reports for date %%',updateday;
	END IF;
END IF;

analyze new_signatures;

-- add product IDs for betas and matching builds
update new_signatures
set product_version_id = product_versions.product_version_id
from product_versions JOIN product_version_builds
	ON product_versions.product_version_id = product_version_builds.product_version_id
where product_versions.release_version = new_signatures.version
	and product_versions.product_name = new_signatures.product
	and product_version_builds.build_id::text = new_signatures.build;

-- add product IDs for builds that don't match
update new_signatures
set product_version_id = product_versions.product_version_id
from product_versions JOIN product_version_builds
	ON product_versions.product_version_id = product_version_builds.product_version_id
where product_versions.release_version = new_signatures.version
	and product_versions.product_name = new_signatures.product
	and product_versions.build_type IN ('release','nightly', 'aurora')
	and new_signatures.product_version_id IS NULL;

analyze new_signatures;

-- update signatures table

insert into signatures ( signature, first_report, first_build )
select new_signatures.signature, min(new_signatures.first_report),
	min(build_numeric(new_signatures.build))
from new_signatures
left outer join signatures
	on new_signatures.signature = signatures.signature
where signatures.signature is null
	and new_signatures.product_version_id is not null
group by new_signatures.signature;

-- update signature_products table

insert into signature_products ( signature_id, product_version_id, first_report )
select signatures.signature_id,
		new_signatures.product_version_id,
		min(new_signatures.first_report)
from new_signatures JOIN signatures
	ON new_signatures.signature = signatures.signature
	left outer join signature_products
		on signatures.signature_id = signature_products.signature_id
		and new_signatures.product_version_id = signature_products.product_version_id
where new_signatures.product_version_id is not null
	and signature_products.signature_id is null
group by signatures.signature_id,
		new_signatures.product_version_id;

-- recreate the rollup from scratch

DELETE FROM signature_products_rollup;

insert into signature_products_rollup ( signature_id, product_name, ver_count, version_list )
select
	signature_id, product_name, count(*) as ver_count,
		array_accum(version_string ORDER BY product_versions.version_sort)
from signature_products JOIN product_versions
	USING (product_version_id)
group by signature_id, product_name;

return true;
end;
$$
"""
	connection.execute(update_signatures)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_socorro_db_version(target, connection, **kw):
	update_socorro_db_version = """
CREATE FUNCTION update_socorro_db_version(newversion text, backfilldate date DEFAULT NULL::date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE rerun BOOLEAN;
BEGIN
	SELECT current_version = newversion
	INTO rerun
	FROM socorro_db_version;
	
	IF rerun THEN
		RAISE NOTICE 'This database is already set to version %%.  If you have deliberately rerun the upgrade scripts, then this is as expected.  If not, then there is something wrong.',newversion;
	ELSE
		UPDATE socorro_db_version SET current_version = newversion;
	END IF;
	
	INSERT INTO socorro_db_version_history ( version, upgraded_on, backfill_to )
		VALUES ( newversion, now(), backfilldate );
	
	RETURN true;
END; $$
"""
	connection.execute(update_socorro_db_version)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_tcbs(target, connection, **kw):
	update_tcbs = """
CREATE FUNCTION update_tcbs(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- this new version depends on reports_clean

-- check that it hasn't already been run

IF checkdata THEN
	PERFORM 1 FROM tcbs
	WHERE report_date = updateday LIMIT 1;
	IF FOUND THEN
		RAISE NOTICE 'TCBS has already been run for the day %%.',updateday;
		RETURN FALSE;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
	ELSE
		RETURN FALSE;
	END IF;
END IF;

-- populate the matview for regular releases

INSERT INTO tcbs (
	signature_id, report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, updateday,
	product_version_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
GROUP BY signature_id, updateday, product_version_id,
	process_type, release_channel;

-- populate summary statistics for rapid beta parent records

INSERT INTO tcbs (
	signature_id, report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count )
SELECT signature_id, updateday, rapid_beta_id,
	process_type, release_channel,
	sum(report_count), sum(win_count), sum(mac_count), sum(lin_count),
	sum(hang_count), sum(startup_count)
FROM tcbs
	JOIN product_versions USING (product_version_id)
WHERE report_date = updateday
	AND build_type = 'beta'
	AND rapid_beta_id is not null
GROUP BY signature_id, updateday, rapid_beta_id,
	process_type, release_channel;

-- tcbs_ranking removed until it's being used

-- done
RETURN TRUE;
END;
$$
"""
	connection.execute(update_tcbs)

@event.listens_for(UptimeLevel.__table__, "before_create")
def update_tcbs_build(target, connection, **kw):
	update_tcbs_build = """
CREATE FUNCTION update_tcbs_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- this new version depends on reports_clean

-- check that it hasn't already been run

IF checkdata THEN
	PERFORM 1 FROM tcbs_build
	WHERE report_date = updateday LIMIT 1;
	IF FOUND THEN
		RAISE NOTICE 'TCBS has already been run for the day %%.',updateday;
		RETURN FALSE;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %%',updateday;
	ELSE
		RAISE INFO 'reports_clean not updated';
		RETURN FALSE;
	END IF;
END IF;

-- populate the matview for nightly and aurora

INSERT INTO tcbs_build (
	signature_id, build_date,
	report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, build_date(build),
	updateday, product_version_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	JOIN products USING ( product_name )
WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
	-- 7 days of builds only
	AND updateday <= ( build_date(build) + 6 )
	-- only nightly, aurora, and rapid beta
	AND reports_clean.release_channel IN ( 'nightly','aurora' )
	AND version_matches_channel(version_string, release_channel)
GROUP BY signature_id, build_date(build), product_version_id,
	process_type, release_channel;

-- populate for rapid beta parent records only

INSERT INTO tcbs_build (
	signature_id, build_date,
	report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, build_date(build),
	updateday, rapid_beta_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	JOIN products USING ( product_name )
WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
	-- 7 days of builds only
	AND updateday <= ( build_date(build) + 6 )
	-- only nightly, aurora, and rapid beta
	AND reports_clean.release_channel = 'beta'
	AND rapid_beta_id is not null
GROUP BY signature_id, build_date(build), rapid_beta_id,
	process_type, release_channel;

-- tcbs_ranking removed until it's being used

-- done
RETURN TRUE;
END;
$$
"""
	connection.execute(update_tcbs_build)

@event.listens_for(UptimeLevel.__table__, "before_create")
def url2domain(target, connection, **kw):
	url2domain = """
CREATE FUNCTION url2domain(some_url text) RETURNS citext
    LANGUAGE sql IMMUTABLE
    AS $_$
select substring($1 FROM $x$^([\w:]+:/+(?:\w+\.)*\w+).*$x$)::citext
$_$
"""
	connection.execute(url2domain)

@event.listens_for(UptimeLevel.__table__, "before_create")
def utc_day_is(target, connection, **kw):
	utc_day_is = """
CREATE FUNCTION utc_day_is(timestamp with time zone, timestamp without time zone) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
select $1 >= ( $2 AT TIME ZONE 'UTC' )
	AND $1 < ( ( $2 + INTERVAL '1 day' ) AT TIME ZONE 'UTC'  );
$_$
"""
	connection.execute(utc_day_is)

@event.listens_for(UptimeLevel.__table__, "before_create")
def utc_day_near(target, connection, **kw):
	utc_day_near = """
CREATE FUNCTION utc_day_near(timestamp with time zone, timestamp without time zone) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
select $1 > ( $2 AT TIME ZONE 'UTC' - INTERVAL '1 day' )
AND $1 < ( $2 AT TIME ZONE 'UTC' + INTERVAL '2 days' )
$_$
"""
	connection.execute(utc_day_near)

@event.listens_for(UptimeLevel.__table__, "before_create")
def validate_lookup(target, connection, **kw):
	validate_lookup = """
CREATE FUNCTION validate_lookup(ltable text, lcol text, lval text, lmessage text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE nrows INT;
BEGIN
	EXECUTE 'SELECT 1 FROM ' || ltable ||
		' WHERE ' || lcol || ' = ' || quote_literal(lval)
	INTO nrows;
	
	IF nrows > 0 THEN
		RETURN true;
	ELSE 
		RAISE EXCEPTION '%% is not a valid %%',lval,lmessage;
	END IF;
END;
$$
"""
	connection.execute(validate_lookup)

@event.listens_for(UptimeLevel.__table__, "before_create")
def version_matches_channel(target, connection, **kw):
	version_matches_channel = """
CREATE FUNCTION version_matches_channel(version text, channel citext) RETURNS boolean
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
SELECT CASE WHEN $1 ILIKE '%%a1' AND $2 ILIKE 'nightly%%'
	THEN TRUE
WHEN $1 ILIKE '%%a2' AND $2 = 'aurora' 
	THEN TRUE
WHEN $1 ILIKE '%%esr' AND $2 IN ( 'release', 'esr' )
	THEN TRUE
WHEN $1 NOT ILIKE '%%a%%' AND $1 NOT ILIKE '%%esr' AND $2 IN ( 'beta', 'release' )
	THEN TRUE
ELSE FALSE END;
$_$
"""
	connection.execute(version_matches_channel)

@event.listens_for(UptimeLevel.__table__, "before_create")
def version_sort(target, connection, **kw):
	version_sort = """
CREATE FUNCTION version_sort(version text, beta_no integer DEFAULT 0, channel citext DEFAULT ''::citext) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $_$
DECLARE vne TEXT[];
	sortstring TEXT;
	dex INT;
BEGIN

	-- regexp the version number into tokens
	vne := regexp_matches( version, $x$^(\d+)\.(\d+)([a-zA-Z]*)(\d*)(?:\.(\d+))?(?:([a-zA-Z]+)(\d*))?.*$$x$ );
	
	-- bump betas after the 3rd digit back
	vne[3] := coalesce(nullif(vne[3],''),vne[6]);
	vne[4] := coalesce(nullif(vne[4],''),vne[7]);

	-- handle betal numbers
	IF beta_no > 0 THEN
		vne[3] := 'b';
		vne[4] := beta_no::TEXT;
	END IF;
	
	--handle final betas
	IF version LIKE '%%(beta)%%' THEN
		vne[3] := 'b';
		vne[4] := '99';
	END IF;
	
	--handle release channels
	CASE channel
		WHEN 'nightly' THEN
			vne[3] := 'a';
			vne[4] := '1';
		WHEN 'aurora' THEN
			vne[3] := 'a';
			vne[4] := '2';
		WHEN 'beta' THEN
			vne[3] := 'b';
			vne[4] := COALESCE(nullif(vne[4],''),99);
		WHEN 'release' THEN
			vne[3] := 'r';
			vne[4] := '0';
		WHEN 'ESR' THEN
			vne[3] := 'x';
			vne[4] := '0';
		ELSE
			NULL;
	END CASE;
	
	-- fix character otherwise
	IF vne[3] = 'esr' THEN
		vne[3] := 'x';
	ELSE
		vne[3] := COALESCE(nullif(vne[3],''),'r');
	END IF;
	
	--assemble string
	sortstring := version_sort_digit(vne[1]) 
		|| version_sort_digit(vne[2]) 
		|| version_sort_digit(vne[5]) 
		|| vne[3]
		|| version_sort_digit(vne[4]) ;
		
	RETURN sortstring;
END;$_$
"""
	connection.execute(version_sort)

@event.listens_for(UptimeLevel.__table__, "before_create")
def version_sort_trigger(target, connection, **kw):
	version_sort_trigger = """
CREATE FUNCTION version_sort_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	-- on insert or update, makes sure that the
	-- version_sort column is correct
	NEW.version_sort := old_version_sort(NEW.version);
	RETURN NEW;
END;
$$
"""
	connection.execute(version_sort_trigger)

@event.listens_for(UptimeLevel.__table__, "before_create")
def version_sort_update_trigger_after(target, connection, **kw):
	version_sort_update_trigger_after = """
CREATE FUNCTION version_sort_update_trigger_after() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
-- update sort keys
PERFORM product_version_sort_number(NEW.product);
RETURN NEW;
END; $$
"""
	connection.execute(version_sort_update_trigger_after)

@event.listens_for(UptimeLevel.__table__, "before_create")
def version_sort_update_trigger_before(target, connection, **kw):
	version_sort_update_trigger_before = """
CREATE FUNCTION version_sort_update_trigger_before() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
-- updates productdims_version_sort
-- should be called only by a cascading update from productdims

-- update sort record
SELECT s1n1,s1s1,s1n2,s1s2,
s2n1,s2s1,s2n2,s2s2,
s3n1,s3s1,s3n2,s3s2,
ext
INTO 
NEW.sec1_num1,NEW.sec1_string1,NEW.sec1_num2,NEW.sec1_string2,
NEW.sec2_num1,NEW.sec2_string1,NEW.sec2_num2,NEW.sec2_string2,
NEW.sec3_num1,NEW.sec3_string1,NEW.sec3_num2,NEW.sec3_string2,
NEW.extra
FROM tokenize_version(NEW.version);

RETURN NEW;
END; $$
"""
	connection.execute(version_sort_update_trigger_before)

@event.listens_for(UptimeLevel.__table__, "before_create")
def version_string(target, connection, **kw):
	version_string = """
CREATE FUNCTION version_string(version text, beta_number integer) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts a stripped version and a beta number
-- into a version string
SELECT CASE WHEN $2 <> 0 THEN
	$1 || 'b' || $2
ELSE
	$1
END;
$_$
"""
	connection.execute(version_string)

@event.listens_for(UptimeLevel.__table__, "before_create")
def version_string(target, connection, **kw):
	version_string = """
CREATE FUNCTION version_string(version text, beta_number integer, channel text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts a stripped version and a beta number
-- into a version string
SELECT CASE WHEN $2 <> 0 THEN
	$1 || 'b' || $2
WHEN $3 ILIKE 'nightly' THEN
	$1 || 'a1'
WHEN $3 ILIKE 'aurora' THEN
	$1 || 'a2'
ELSE
	$1
END;
$_$
"""
	connection.execute(version_string)

@event.listens_for(UptimeLevel.__table__, "before_create")
def watch_report_processing(target, connection, **kw):
	watch_report_processing = """
CREATE FUNCTION watch_report_processing(INOUT run_min integer, OUT report_count integer, OUT min_time interval, OUT max_time interval, OUT avg_time interval) RETURNS record
    LANGUAGE plpgsql
    AS $$
declare reprec RECORD;
    cur_min interval;
    cur_max interval := '0 seconds';
    cur_tot interval := '0 seconds';
    cur_avg interval;
    cur_lag interval;
    cur_count int;
    last_report timestamp;
    end_time timestamptz;
    cur_time timestamptz;
    start_count int;
    start_time timestamptz;
    cur_loop INT := 0;
begin
  end_time := now() + run_min * interval '1 minute';
  start_time := now();

  select count(*) into start_count
  from reports where date_processed > ( start_time - interval '2 days' )
    and completed_datetime is not null;
  cur_time = clock_timestamp();

  while  cur_time < end_time loop

    select max(date_processed),
      count(*) - start_count
    into last_report, cur_count
    from reports where date_processed > ( start_time - interval '2 days' )
      and completed_datetime is not null;

    cur_loop := cur_loop + 1;
    cur_lag := cur_time - last_report;
    cur_tot := cur_tot + cur_lag;
    cur_min := LEAST(cur_min, cur_lag);
    cur_max := GREATEST(cur_max, cur_lag);
    cur_avg := cur_tot / cur_loop;

    RAISE INFO 'At: %% Last Report: %%',to_char(cur_time,'Mon DD HH24:MI:SS'),to_char(last_report,'Mon DD HH24:MI:SS');
    RAISE INFO 'Count: %%   Lag: %%  Min: %%   Max: %%   Avg: %%', cur_count, to_char(cur_lag,'HH24:MI:SS'),to_char(cur_min, 'HH24:MI:SS'),to_char(cur_max, 'HH24:MI:SS'),to_char(cur_avg,'HH24:MI:SS');

    perform pg_sleep(10);
    cur_time := clock_timestamp();

  end loop;

  report_count := cur_count;
  min_time := cur_min;
  max_time := cur_max;
  avg_time := cur_avg;
  return;

  end;
$$
"""
	connection.execute(watch_report_processing)

@event.listens_for(UptimeLevel.__table__, "before_create")
def week_begins_partition(target, connection, **kw):
	week_begins_partition = """
CREATE FUNCTION week_begins_partition(partname text) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_timestamp( substring($1 from $x$\d+$$x$), 'YYYYMMDD' );
$_$
"""
	connection.execute(week_begins_partition)

@event.listens_for(UptimeLevel.__table__, "before_create")
def week_begins_partition_string(target, connection, **kw):
	week_begins_partition_string = """
CREATE FUNCTION week_begins_partition_string(partname text) RETURNS text
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_char( week_begins_partition( $1 ), 'YYYY-MM-DD' ) || ' 00:00:00 UTC';
$_$
"""
	connection.execute(week_begins_partition_string)

@event.listens_for(UptimeLevel.__table__, "before_create")
def week_begins_utc(target, connection, **kw):
	week_begins_utc = """
CREATE FUNCTION week_begins_utc(timestamp with time zone) RETURNS timestamp with time zone
    LANGUAGE sql STABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT date_trunc('week', $1);
$_$
"""
	connection.execute(week_begins_utc)

@event.listens_for(UptimeLevel.__table__, "before_create")
def week_ends_partition(target, connection, **kw):
	week_ends_partition = """
CREATE FUNCTION week_ends_partition(partname text) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_timestamp( substring($1 from $x$\d+$$x$), 'YYYYMMDD' ) + INTERVAL '7 days';
$_$
"""
	connection.execute(week_ends_partition)

@event.listens_for(UptimeLevel.__table__, "before_create")
def week_ends_partition_string(target, connection, **kw):
	week_ends_partition_string = """
CREATE FUNCTION week_ends_partition_string(partname text) RETURNS text
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_char( week_ends_partition( $1 ), 'YYYY-MM-DD' ) || ' 00:00:00 UTC';
$_$
"""
	connection.execute(week_ends_partition_string)

@event.listens_for(UptimeLevel.__table__, "before_create")
def weekly_report_partitions(target, connection, **kw):
	weekly_report_partitions = """
CREATE FUNCTION weekly_report_partitions(numweeks integer DEFAULT 2, targetdate timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function checks that we have partitions two weeks into
-- the future for each of the tables associated with
-- reports
-- designed to be called as a cronjob once a week
-- controlled by the data in the reports_partition_info table
DECLARE 
	thisweek DATE;
	dex INT := 1;
	weeknum INT := 0;
	tabinfo RECORD;
BEGIN
	targetdate := COALESCE(targetdate, now());
	thisweek := date_trunc('week', targetdate)::date;
	
	WHILE weeknum <= numweeks LOOP
		FOR tabinfo IN SELECT * FROM report_partition_info
			ORDER BY build_order LOOP
			
			PERFORM create_weekly_partition ( 
				tablename := tabinfo.table_name,
				theweek := thisweek,
				uniques := tabinfo.keys,
				indexes := tabinfo.indexes,
				fkeys := tabinfo.fkeys,
				tableowner := 'breakpad_rw'
			);

		END LOOP;
		weeknum := weeknum + 1;
		thisweek := thisweek + 7;
	END LOOP;

	RETURN TRUE;
	
END; $$
"""
	connection.execute(weekly_report_partitions)


###########################################
## Connection management
###########################################

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


###########################################
##  Database creation object
###########################################
class SocorroDB(App):
    """
    SocorroDB
        This function creates a base PostgreSQL schema for Socorro

    Notes:

        All functions declared need '%' to be escaped as '%%'

    """
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

        # Connect to our new database
        self.engine = create_engine(sa_url)
        self.engine.connect()

        # Bind to a session (so we can explicitly commit)
        self.session = sessionmaker(bind=self.engine)()

        # Extract and bind metadata object containing our schema definition
        metadata = DeclarativeBase.metadata
        metadata.bind = self.engine

        # Create all tables, views and functions
        # Functions are created before the Address table
        metadata.create_all(self.engine)

        # TODO alter all table ownerships to configurable owner
        self.session.execute('ALTER DATABASE %s OWNER TO breakpad_rw'
                        % self.database_name)

        self.session.commit()

        return 0

if __name__ == "__main__":
    sys.exit(main(SocorroDB))

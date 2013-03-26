#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
SQLAlchemy models for Socorro
"""
from __future__ import unicode_literals

from sqlalchemy import *
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.ext import compiler
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import table
import sqlalchemy.types as types

try:
    from sqlalchemy.dialects.postgresql import *
except ImportError:
    from sqlalchemy.databases.postgres import *

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


###########################################
# Baseclass for all Socorro tables
###########################################

DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata

from sqlalchemy.dialects.postgresql.base import ischema_names
ischema_names['citext'] = CITEXT
ischema_names['json'] = JSON


###############################
# Schema definition: Tables
###############################

class EmailCampaignsContact(DeclarativeBase):
    __tablename__ = 'email_campaigns_contacts'

    #column definitions
    email_campaigns_id = Column(u'email_campaigns_id', INTEGER(), ForeignKey('email_campaigns.id'))
    email_contacts_id = Column(u'email_contacts_id', INTEGER(), ForeignKey('email_contacts.id'))
    status = Column(u'status', TEXT(), nullable=False, server_default='stopped')

    __mapper_args__ = {"primary_key":(email_campaigns_id, email_contacts_id)}

class Tcbs(DeclarativeBase):
    __tablename__ = 'tcbs'

    #column definitions
    signature_id = Column(u'signature_id', INTEGER(), ForeignKey('signatures.signature_id'), primary_key=True, nullable=False, index=True)
    report_date = Column(u'report_date', DATE(), primary_key=True, nullable=False, index=True)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
    process_type = Column(u'process_type', CITEXT(), primary_key=True, nullable=False)
    release_channel = Column(u'release_channel', CITEXT(), ForeignKey('release_channels.release_channel'), primary_key=True, nullable=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, server_default=text('0'))
    win_count = Column(u'win_count', INTEGER(), nullable=False, server_default=text('0'))
    mac_count = Column(u'mac_count', INTEGER(), nullable=False, server_default=text('0'))
    lin_count = Column(u'lin_count', INTEGER(), nullable=False, server_default=text('0'))
    hang_count = Column(u'hang_count', INTEGER(), nullable=False, server_default=text('0'))
    startup_count = Column(u'startup_count', INTEGER())

    idx_tcbs_product_version = Index('idx_tcbs_product_version', product_version_id, report_date)

class CorrelationAddon(DeclarativeBase):
    __tablename__ = 'correlation_addons'

    #column definitions
    correlation_id = Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False)
    addon_key = Column(u'addon_key', TEXT(), nullable=False)
    addon_version = Column(u'addon_version', TEXT(), nullable=False)
    crash_count = Column(u'crash_count', INTEGER(), nullable=False, server_default=text('0'))

    __mapper_args__ = {"primary_key":(correlation_id, addon_key, addon_version)}
    correlation_addons_key = Index('correlation_addons_key', correlation_id, addon_key, addon_version, unique=True)

class CorrelationCore(DeclarativeBase):
    __tablename__ = 'correlation_cores'

    #column definitions
    correlation_id = Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False)
    architecture = Column(u'architecture', CITEXT(), nullable=False)
    cores = Column(u'cores', INTEGER(), nullable=False)
    crash_count = Column(u'crash_count', INTEGER(), nullable=False, server_default=text('0'))

    __mapper_args__ = {"primary_key":(correlation_id, architecture, cores)}
    correlation_cores_key = Index(u'correlation_cores_key', correlation_id, architecture, cores, unique=True)


class CorrelationModule(DeclarativeBase):
    __tablename__ = 'correlation_modules'

    #column definitions
    correlation_id = Column(u'correlation_id', INTEGER(), ForeignKey('correlations.correlation_id'), nullable=False)
    module_signature = Column(u'module_signature', TEXT(), nullable=False)
    module_version = Column(u'module_version', TEXT(), nullable=False)
    crash_count = Column(u'crash_count', INTEGER(), nullable=False, server_default=text('0'))

    __mapper_args__ = {"primary_key":(correlation_id, module_signature, module_version)}
    correlation_modules_key = Index(u'correlation_modules_key', correlation_id, module_signature, module_version, unique=True)

class Extension(DeclarativeBase):
    __tablename__ = 'extensions'

    #column definitions
    report_id = Column(u'report_id', INTEGER(), nullable=False)
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True))
    extension_key = Column(u'extension_key', INTEGER(), nullable=False)
    extension_id = Column(u'extension_id', TEXT(), nullable=False)
    extension_version = Column(u'extension_version', TEXT())

    __mapper_args__ = {"primary_key":(report_id, date_processed, extension_key, extension_id, extension_version)}

class PluginsReport(DeclarativeBase):
    __tablename__ = 'plugins_reports'

    #column definitions
    report_id = Column(u'report_id', INTEGER(), nullable=False)
    plugin_id = Column(u'plugin_id', INTEGER(), nullable=False)
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True))
    version = Column(u'version', TEXT(), nullable=False)

    __mapper_args__ = {"primary_key":(report_id, plugin_id, date_processed, version)}

class PriorityjobsLog(DeclarativeBase):
    __tablename__ = 'priorityjobs_log'

    #column definitions
    uuid = Column(u'uuid', VARCHAR(length=255))
    __mapper_args__ = {"primary_key":(uuid)}

class RawAdu(DeclarativeBase):
    __tablename__ = 'raw_adu'

    #column definitions
    adu_count = Column(u'adu_count', INTEGER())
    date = Column(u'date', DATE())
    product_name = Column(u'product_name', TEXT())
    product_os_platform = Column(u'product_os_platform', TEXT())
    product_os_version = Column(u'product_os_version', TEXT())
    product_version = Column(u'product_version', TEXT())
    build = Column(u'build', TEXT())
    build_channel = Column(u'build_channel', TEXT())
    product_guid = Column(u'product_guid', TEXT())
    received_at = Column(u'received_at', TIMESTAMP(timezone=True), server_default=text('NOW()'))

    raw_adu_1_idx = Index(u'raw_adu_1_idx', date, product_name, product_version, product_os_platform, product_os_version)
    __mapper_args__ = {"primary_key":(adu_count, date, product_name, product_version, product_os_platform, product_os_version, build, build_channel, product_guid)}

class ReplicationTest(DeclarativeBase):
    __tablename__ = 'replication_test'

    #column definitions
    id = Column(u'id', SMALLINT())
    test = Column(u'test', BOOLEAN())

    __mapper_args__ = {"primary_key":(id, test)}

class ReportsBad(DeclarativeBase):
    __tablename__ = 'reports_bad'
    uuid = Column(u'uuid', TEXT(), nullable=False)
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True), nullable=False)

    __mapper_args__ = {"primary_key":(uuid)}

class WindowsVersion(DeclarativeBase):
    __tablename__ = 'windows_versions'
    windows_version_name = Column(u'windows_version_name', CITEXT(), nullable=False)
    major_version = Column(u'major_version', INTEGER(), nullable=False)
    minor_version = Column(u'minor_version', INTEGER(), nullable=False)

    windows_version_key = Index('windows_version_key', major_version, minor_version, unique=True)

    __mapper_args__ = {"primary_key":(major_version, minor_version)}

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
    completed_datetime = Column(u'completed_datetime', TIMESTAMP(timezone=True))
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
    release_channel = Column(u'release_channel', TEXT())
    productid = Column(u'productid', TEXT())
    exploitability = Column(u'exploitability', TEXT())

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
    bug_id = Column(u'bug_id', INTEGER(), ForeignKey('bugs.id'), primary_key=True, nullable=False, index=True)
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

    # Indexes
    daily_hangs_browser_signature_id = Index('daily_hangs_browser_signature_id', browser_signature_id)
    daily_hangs_flash_version_id = Index('daily_hangs_flash_version_id', flash_version_id)
    daily_hangs_hang_id = Index('daily_hangs_hang_id', hang_id)
    daily_hangs_plugin_signature_id = Index('daily_hangs_plugin_signature_id', plugin_signature_id)
    daily_hangs_product_version_id = Index('daily_hangs_product_version_id', product_version_id)
    daily_hangs_report_date = Index('daily_hangs_report_date', report_date)
    daily_hangs_uuid = Index('daily_hangs_uuid', uuid)

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
    email_contacts = relationship('EmailContact', primaryjoin='EmailCampaign.id==email_campaigns_contacts.c.email_campaigns_id', secondary='EmailCampaignsContact', secondaryjoin='EmailCampaignsContact.email_contacts_id==EmailContact.id')

    # Indexes
    email_campaigns_product_signature_key = Index('email_campaigns_product_signature_key', product, signature);


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
    email_campaigns = relationship('EmailCampaign', primaryjoin='EmailContact.id==EmailCampaignsContact.email_contacts_id', secondary='EmailCampaignsContact', secondaryjoin='EmailCampaignsContact.email_campaigns_id==EmailCampaign.id')

class Email(DeclarativeBase):
    __tablename__ = 'emails'

    __table_args__ = {}

    #column definitions
    email = Column(u'email', CITEXT(), nullable=False, primary_key=True)
    last_sending = Column(u'last_sending', TIMESTAMP(timezone=True))


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
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False, index=True)
    signature_id = Column(u'signature_id', INTEGER(), primary_key=True, nullable=False, index=True)
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
    id = Column(u'id', INTEGER(), primary_key=True, nullable=False)
    message = Column(u'message', TEXT())
    owner = Column(u'owner', INTEGER(), ForeignKey('processors.id'))
    pathname = Column(u'pathname', VARCHAR(length=1024), nullable=False)
    priority = Column(u'priority', INTEGER(), server_default=text('0'))
    queueddatetime = Column(u'queueddatetime', TIMESTAMP(timezone=True))
    starteddatetime = Column(u'starteddatetime', TIMESTAMP(timezone=True))
    completeddatetime = Column(u'completeddatetime', TIMESTAMP(timezone=True))
    success = Column(u'success', BOOLEAN())
    uuid = Column(u'uuid', VARCHAR(length=50), nullable=False)

    #relationship definitions
    processors = relationship('Processor', primaryjoin='Job.owner==Processor.id')

    # Indexes
    jobs_completeddatetime_queueddatetime_key = Index('jobs_completeddatetime_queueddatetime_key', completeddatetime, queueddatetime)
    jobs_owner_starteddatetime_key = Index('jobs_owner_starteddatetime_key', owner, starteddatetime)


class NightlyBuild(DeclarativeBase):
    __tablename__ = 'nightly_builds'

    __table_args__ = {}

    #column definitions
    build_date = Column(u'build_date', DATE(), primary_key=True, nullable=False)
    days_out = Column(u'days_out', INTEGER(), primary_key=True, nullable=False)
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False)
    report_count = Column(u'report_count', INTEGER(), nullable=False, server_default=text('0'))
    report_date = Column(u'report_date', DATE(), nullable=False)

    # Indexes
    nightly_builds_product_version_id_report_date = Index('nightly_builds_product_version_id_report_date', product_version_id, report_date)


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
    release_channels = relationship('ReleaseChannel', primaryjoin='Product.product_name==ProductReleaseChannel.product_name', secondary='ProductReleaseChannel', secondaryjoin='ProductReleaseChannel.release_channel==ReleaseChannel.release_channel')
    product_versions = relationship('Product', primaryjoin='Product.product_name==ProductVersion.product_name', secondary='ProductVersion', secondaryjoin='ProductVersion.rapid_beta_id==ProductVersion.product_version_id')
    signatures = relationship('Signature', primaryjoin='Product.product_name==SignatureProductsRollup.product_name', secondary='SignatureProductsRollup', secondaryjoin='SignatureProductsRollup.signature_id==Signature.signature_id')


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
    __tablename__ = 'product_release_channels'

    #column definitions
    product_name = Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), primary_key=True, nullable=False)
    release_channel = Column(u'release_channel', CITEXT(), ForeignKey('release_channels.release_channel'), primary_key=True, nullable=False)
    throttle = Column(u'throttle', NUMERIC(), nullable=False, server_default=text('1.0'))

    #relationship definitions
    release_channels = relationship('ReleaseChannel', primaryjoin='ProductReleaseChannel.release_channel==ReleaseChannel.release_channel')
    products = relationship('Product', primaryjoin='ProductReleaseChannel.product_name==Product.product_name')


class ProductVersion(DeclarativeBase):
    __tablename__ = 'product_versions'

    #column definitions
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False)
    product_name = Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), nullable=False, index=True)
    major_version = Column(u'major_version', TEXT(), index=True)
    release_version = Column(u'release_version', CITEXT(), nullable=False)
    version_string = Column(u'version_string', CITEXT(), nullable=False)
    beta_number = Column(u'beta_number', INTEGER())
    version_sort = Column(u'version_sort', TEXT(), nullable=False, server_default="0", index=True)
    build_date = Column(u'build_date', DATE(), nullable=False)
    sunset_date = Column(u'sunset_date', DATE(), nullable=False)
    featured_version = Column(u'featured_version', BOOLEAN(), nullable=False, server_default=text('False'))
    build_type = Column(u'build_type', CITEXT(), nullable=False, server_default='release')
    has_builds = Column(u'has_builds', BOOLEAN())
    is_rapid_beta = Column(u'is_rapid_beta', BOOLEAN(), server_default=text('False'))
    rapid_beta_id = Column(u'rapid_beta_id', INTEGER(), ForeignKey('product_versions.product_version_id'))

    #relationship definitions
    products = relationship('Product', primaryjoin='ProductVersion.product_version_id==ProductVersion.rapid_beta_id', secondary='ProductVersion', secondaryjoin='ProductVersion.product_name==Product.product_name')
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
    signature_id = Column(u'signature_id', INTEGER(), primary_key=True, nullable=False, index=True)
    total_reports = Column(u'total_reports', BIGINT())

    # Indexes
    rank_compare_product_version_id_rank_report_count = Index('rank_compare_product_version_id_rank_report_count', product_version_id, rank_report_count)

class RawCrashes(DeclarativeBase):
    __tablename__ = 'raw_crashes'

    __table_args__ = {}

    #column definitions
    uuid = Column(u'uuid', UUID(), nullable=False, index=True, unique=True)
    raw_crash = Column(u'raw_crash', JSON(), nullable=False)
    date_processed = Column(u'date_processed', TIMESTAMP(timezone=True))

    #relationship definitions
    __mapper_args__ = {"primary_key":(uuid)}


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
    products = relationship('Product', primaryjoin='ReleaseChannel.release_channel==ProductReleaseChannel.release_channel', secondary='ProductReleaseChannel', secondaryjoin='ProductReleaseChannel.product_name==Product.product_name')
    signatures = relationship('Signature', primaryjoin='ReleaseChannel.release_channel==Tcbs.release_channel', secondary='Tcbs', secondaryjoin='Tcbs.signature_id==Signature.signature_id')


class ReleaseChannelMatch(DeclarativeBase):
    __tablename__ = 'release_channel_matches'

    __table_args__ = {}

    #column definitions
    match_string = Column(u'match_string', TEXT(), primary_key=True, nullable=False)
    release_channel = Column(u'release_channel', CITEXT(), ForeignKey('release_channels.release_channel'), primary_key=True, nullable=False)

    #relationship definitions
    release_channels = relationship('ReleaseChannel', primaryjoin='ReleaseChannelMatch.release_channel==ReleaseChannel.release_channel')


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
    # TODO function-based index
    #releases_raw_date = Index('releases_raw_date', DDL('create index releases_raw_date on releases_raw(build_date(build_id))'));


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
    duplicate_of = Column(u'duplicate_of', TEXT(), nullable=False, index=True)
    uuid = Column(u'uuid', TEXT(), primary_key=True, nullable=False)

    # Indexes
    reports_duplicates_timestamp = Index('reports_duplicates_timestamp', date_processed, uuid)


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

    # Index
    idx_server_status_date = Index('idx_server_status_date', date_created, id)


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
    products = relationship('Product', primaryjoin='Signature.signature_id==SignatureProductsRollup.signature_id', secondary='SignatureProductsRollup', secondaryjoin='SignatureProductsRollup.product_name==Product.product_name')
    release_channels = relationship('ReleaseChannel', primaryjoin='Signature.signature_id==Tcbs.signature_id', secondary='Tcbs', secondaryjoin='Tcbs.release_channel==ReleaseChannel.release_channel')


class SignatureProduct(DeclarativeBase):
    __tablename__ = 'signature_products'

    __table_args__ = {}

    #column definitions
    first_report = Column(u'first_report', TIMESTAMP(timezone=True))
    product_version_id = Column(u'product_version_id', INTEGER(), primary_key=True, nullable=False, autoincrement=False, index=True)
    signature_id = Column(u'signature_id', INTEGER(), ForeignKey('signatures.signature_id'), primary_key=True, nullable=False)

    #relationship definitions
    signatures = relationship('Signature', primaryjoin='SignatureProduct.signature_id==Signature.signature_id')

class SignatureProductsRollup(DeclarativeBase):
    __tablename__ = 'signature_products_rollup'

    signature_id = Column(u'signature_id', INTEGER(), ForeignKey('signatures.signature_id'), primary_key=True, nullable=False)
    product_name = Column(u'product_name', CITEXT(), ForeignKey('products.product_name'), primary_key=True, nullable=False)
    ver_count = Column(u'ver_count', INTEGER(), nullable=False, server_default=text('0'))
    version_list = Column(u'version_list', ARRAY(TEXT()), nullable=False, server_default=text("'{}'::text[]"))

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

# Depends on content_count_state() function 
#@event.listens_for(UptimeLevel.__table__, "after_create")
#def content_count(target, connection, **kw):
    #content_count = """
#CREATE AGGREGATE content_count(citext, integer) (
    #SFUNC = content_count_state,
    #STYPE = integer,
    #INITCOND = '0'
#)
#"""
    #connection.execute(content_count)

# Depends on plugin_count_state() function
#@event.listens_for(UptimeLevel.__table__, "after_create")
#def plugin_count(target, connection, **kw):
    #plugin_count = """
#CREATE AGGREGATE plugin_count(citext, integer) (
    #SFUNC = plugin_count_state,
    #STYPE = integer,
    #INITCOND = '0'
#)
#"""
    #connection.execute(plugin_count)


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

# TODO Document where this is used in the schema
#      Might need to create a custom type in SQLA
#@event.listens_for(UptimeLevel.__table__, "before_create")
#def create_socorro_domains(target, connection, **kw):
    #major_version = """
#CREATE DOMAIN major_version AS text
#	CONSTRAINT major_version_check CHECK ((VALUE ~ '^\d+\.\d+'::text))
#"""
#       connection.execute(major_version)




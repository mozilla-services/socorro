# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import gzip
import csv
import os.path
import re

import contextlib


from configman import Namespace

from crontabber.mixins import (
    using_postgres,
    with_subprocess,
    as_backfill_cron_app
)
from crontabber.base import BaseCronApp

from socorro.external.postgresql.dbapi2_util import (
    execute_no_results
)
from socorro.lib.util import DotDict


sql = """
      select
        r.signature,  -- 0
        r.url,        -- 1
        'http://crash-stats.mozilla.com/report/index/' || r.uuid as uuid_url, -- 2
        to_char(r.client_crash_date,'YYYYMMDDHH24MI') as client_crash_date,   -- 3
        to_char(r.date_processed,'YYYYMMDDHH24MI') as date_processed,         -- 4
        r.last_crash, -- 5
        r.product,    -- 6
        r.version,    -- 7
        r.build,      -- 8
        '' as branch, -- 9
        r.os_name,    --10
        r.os_version, --11
        r.cpu_name || ' | ' || r.cpu_info as cpu_info,   --12
        r.address,    --13
        array(select ba.bug_id from bug_associations ba where ba.signature = r.signature) as bug_list, --14
        r.user_comments, --15
        r.uptime as uptime_seconds, --16
        case when (r.email is NULL OR r.email='') then '' else r.email end as email, --17
        (select sum(adi_count) from raw_adi adi
           where adi.date = '%(now_str)s'
             and r.product = adi.product_name and r.version = adi.product_version
             and substring(r.os_name from 1 for 3) = substring(adi.product_os_platform from 1 for 3)
             and r.os_version LIKE '%%'||adi.product_os_version||'%%') as adu_count, --18
        r.topmost_filenames, --19
        case when (r.addons_checked is NULL) then '[unknown]'when (r.addons_checked) then 'checked' else 'not' end as addons_checked, --20
        r.flash_version, --21
        r.hangid, --22
        r.reason, --23
        r.process_type, --24
        r.app_notes, --25
        r.install_age, --26
        rd.duplicate_of, --27
        r.release_channel, --28
        r.productid --29
      from
        reports r left join reports_duplicates rd on r.uuid = rd.uuid
      where
        '%(yesterday_str)s' <= r.date_processed and r.date_processed < '%(now_str)s'
        %(prod_phrase)s %(ver_phrase)s
      order by 5 -- r.date_processed, munged
      """


#------------------------------------------------------------------------------
def setup_query_parameters(config, day):
    now = day + datetime.timedelta(1)
    now_str = now.strftime('%Y-%m-%d')
    yesterday = day
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    config.logger.debug(
        "day = %s; now = %s; yesterday = %s",
        day,
        now,
        yesterday
    )
    prod_phrase = ''
    try:
        if config.product != '':
            if ',' in config.product:
                prod_list = [x.strip() for x in config.product.split(',')]
                prod_phrase = (
                    "and r.product in ('%s')" % "','".join(prod_list)
                )
            else:
                prod_phrase = "and r.product = '%s'" % config.product
    except Exception, x:
        config.logger.error(
            'unable to create product phrase for query',
            exc_info=True
        )
    ver_phrase = ''
    try:
        if config.version != '':
            if ',' in config.product:
                ver_list = [v.strip() for v in config.version.split(',')]
                ver_phrase = ("and r.version in ('%s')" % "','".join(ver_list))
            else:
                ver_phrase = "and r.version = '%s'" % config.version
    except Exception, x:
        config.logger.error(
            'unable to create product phrase for query',
            exc_info=True
        )

    return DotDict({
        'now_str': now_str,
        'yesterday_str': yesterday_str,
        'prod_phrase': prod_phrase,
        'ver_phrase': ver_phrase
    })


#------------------------------------------------------------------------------
@contextlib.contextmanager
def gzipped_csv_files(config, day, gzip=gzip, csv=csv):
    private_out_filename = (
        "%s-crashdata.csv.gz" % day.strftime('%Y%m%d')
    )
    private_out_pathname = os.path.join(
        config.output_path,
        private_out_filename
    )
    config.private_out_pathname = private_out_pathname
    private_gzip_file_handle = gzip.open(private_out_pathname, "w")
    private_csv_file_handle = csv.writer(
        private_gzip_file_handle,
        delimiter='\t',
        lineterminator='\n'
    )

    public_out_filename = "%s-pub-crashdata.csv.gz" % day.strftime('%Y%m%d')
    public_out_pathname = None
    public_out_directory = config.get('public_output_path')
    public_gzip_file_handle = None
    public_csv_file_handle = None
    if public_out_directory:
        public_out_pathname = os.path.join(
            public_out_directory,
            public_out_filename
        )
        public_gzip_file_handle = gzip.open(public_out_pathname, "w")
        public_csv_file_handle = csv.writer(
            public_gzip_file_handle,
            delimiter='\t',
            lineterminator='\n'
        )
    else:
        config.logger.info("Will not create public (bowdlerized) gzip file")
    config.public_out_pathname = public_out_pathname
    yield (private_csv_file_handle, public_csv_file_handle)
    private_gzip_file_handle.close()
    if public_gzip_file_handle:
        public_gzip_file_handle.close()


#------------------------------------------------------------------------------
linux_line_re = re.compile(
    r'0\.0\.0 [lL]inux.+[lL]inux$|[0-9.]+.+(i586|i686|sun4u|i86pc|x86_64)?'
)
linux_version_re = re.compile(
    r'(0\.0\.0 [lL]inux.)([0-9.]+[0-9]).*(i586|i686|sun4u|i86pc|x86_64).*'
)
linux_short_version_re = re.compile(r'(0\.0\.0 [lL]inux.)([0-9.]+[0-9]).*')


#------------------------------------------------------------------------------
def get_appropriat_os_version(name, original_version):
    """
    If this is a linux os, chop out all the gubbish retaining only the actual
    version numbers and, if available, the architecture name.
    """
    ret = original_version
    if 'Linux' != name:
        pass
    elif not linux_line_re.match(original_version):
        ret = ''
    else:
        m = linux_version_re.sub(r'\2 \3', original_version)
        ret = m
        if original_version == m:
            m = linux_short_version_re.sub(r'\2', original_version)
            ret = "%s ?arch?" % (m)
            if original_version == m:
                ret = ''
    return ret


#------------------------------------------------------------------------------
def process_crash(a_crash_row):
    column_value_list = []
    os_name = None
    ooid = ''
    for i, x in enumerate(a_crash_row):
        if x is None:
            x = r'\N'
        if i == 2:
            ooid = x.rsplit('/', 1)[-1]  # existing Bug - unused
        if i == 10:  # r.os_name
            x = os_name = x.strip()
        if i == 11:  # r.os_version
            # per bug 519703
            x = get_appropriat_os_version(os_name, x)
            os_name = None
        if i == 14:  # bug_associations.bug_id
            x = ','.join(str(bugid) for bugid in x)
        if i == 15:  # r.user_comments
            x = x.replace('\t', ' ')  # per bug 519703
        if i == 17:  # r.email -- show 'email' if the email is likely useful
            # per bugs 529431/519703
            if '@' in x:
                x = 'yes'
            else:
                x = ''
        if type(x) == str:
            x = x.strip().replace('\r', '').replace('\n', ' | ')
        column_value_list.append(x)
    return column_value_list


#------------------------------------------------------------------------------
def write_row(file_handles_tuple,
              crash_list):
    """
    Write a row to each file: Seen by internal users (full details), and
    external users (bowdlerized)
    """
    private_file_handle, public_file_handle = file_handles_tuple
    # config.logger.debug("Writing crash %s (%s)",crash_list,len(crash_list))
    private_file_handle.writerow(crash_list)
    crash_list[1] = 'URL (removed)'  # remove url
    crash_list[17] = ''  # remove email
    if public_file_handle:
        public_file_handle.writerow(crash_list)


#------------------------------------------------------------------------------
def dailyUrlDump(
    connection,
    config,
    day,
    get_output_context=gzipped_csv_files,
    write_row=write_row,
    process_crash=process_crash
):

    try:
        with get_output_context(config, day) as output_context:
            execute_no_results(
                connection,
                """ SET TEMP_BUFFERS = %s """,
                (config.database_temp_buffer_size,)
            )

            sql_parameters = setup_query_parameters(config, day)
            config.logger.debug(
                "day = %s; now = %s; yesterday = %s",
                day,
                sql_parameters.now_str,
                sql_parameters.yesterday_str
            )

            with connection.cursor() as db_cursor:
                sql_query = sql % sql_parameters
                config.logger.debug("SQL is: %s", sql_query)
                db_cursor.execute(sql_query)
                headers_not_yet_written = True
                while True:
                    crash_row = db_cursor.fetchone()
                    if crash_row is None:
                        break
                    if headers_not_yet_written:
                        write_row(
                            output_context,
                            [x[0] for x in db_cursor.description]
                        )
                        headers_not_yet_written = False
                    column_value_list = process_crash(crash_row)
                    write_row(output_context, column_value_list)
    except Exception, x:
        config.logger.error(
            'major problem running dailyUrlDump',
            exc_info=True
        )
        raise


#==============================================================================
@as_backfill_cron_app
@with_subprocess
@using_postgres()
class DailyURLCronApp(BaseCronApp):
    app_name = 'daily-url'
    app_version = '2.0'
    app_description = ""

    required_config = Namespace()
    required_config.add_option(
        'database_temp_buffer_size',
        default='8MB',
        doc="size of database TEMP_BUFFERS"
    )
    required_config.add_option(
        'output_path',
        default=None,
        doc="where to write the private data"
    )
    required_config.add_option(
        'public_output_path',
        default=None,
        doc="where to write the public data"
    )
    required_config.add_option(
        'product',
        default='Firefox',
        doc="name of the product to get the report for"
    )
    required_config.add_option(
        'version',
        default='',
        doc="a comma delimited list of the versions to track "
            "(leave blank for all)"
    )    # private scp
    required_config.add_option(
        'private_user',
        default='',
        doc="User that will scp/ssh the private file"
    )
    required_config.add_option(
        'private_server',
        default='',
        doc="Server to scp/ssh to"
    )
    required_config.add_option(
        'private_location',
        default='/tmp/',
        doc="FS location to scp the file to"
    )
    required_config.add_option(
        'private_ssh_command',
        default='',
        doc="Optional extra ssh command to send"
    )
    # public scp
    required_config.add_option(
        'public_user',
        default='',
        doc="User that will scp/ssh the public file"
    )
    required_config.add_option(
        'public_server',
        default='',
        doc="Server to scp/ssh to"
    )
    required_config.add_option(
        'public_location',
        default='/tmp/%Y-%m-%d/',
        doc="FS location to scp the file to"
    )
    required_config.add_option(
        'public_ssh_command',
        default='',
        doc="Optional extra ssh command to send"
    )

    #--------------------------------------------------------------------------
    def scp_file(self, file_path, day, public=False):
        if public:
            user = self.config.public_user
            server = self.config.public_server
            location = self.config.public_location
            ssh_command = self.config.public_ssh_command
        else:
            user = self.config.private_user
            server = self.config.private_server
            location = self.config.private_location
            ssh_command = self.config.private_ssh_command

        if '%' in location:
            location = day.strftime(location)

        if not server:
            return

        if user:
            user += '@'

        command = 'scp "%s" "%s%s:%s"' % (file_path, user, server, location)
        exit_code, stdout, stderr = self.run_process(command)
        if stderr:
            self.config.logger.warn(
                "Error when scp'ing the file %s: %s" % (file_path, stderr)
            )
        if ssh_command:
            command = 'ssh "%s%s" "%s"' % (user, server, ssh_command)
            exit_code, stdout, stderr = self.run_process(command)
            if stderr:
                self.config.logger.warn(
                    "Error when sending ssh command (%s): %s"
                    % (ssh_command, stderr)
                )

    #--------------------------------------------------------------------------
    def run(self, date):
        day = (date - datetime.timedelta(days=1)).date()
        self.database_transaction_executor(dailyUrlDump, self.config, day)

        self.scp_file(self.config.private_out_pathname, day)
        if self.config.public_output_path:
            self.scp_file(self.config.public_output_path, day, public=True)

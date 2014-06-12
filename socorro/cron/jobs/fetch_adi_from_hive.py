# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import urllib2
import csv
import getpass
import os
import tempfile

import pyhs2

from configman import Namespace
from crontabber.base import BaseCronApp
from crontabber.mixins import (
    as_backfill_cron_app,
    with_postgres_transactions,
    with_single_postgres_transaction
)

"""
 Detailed documentation on columns avaiable from our Hive system at:
 https://intranet.mozilla.org/Metrics/Blocklist

 Columns being queried are:
    report_date
    product_name
    product_os_platform
    product_os_version
    product_version
    build
    build_channel
    product_guid
    count
"""

_QUERY = """
    select
        ds,
        split(request_url,'/')[5],
        split(split(request_url,'/')[10], '%%20')[0],
        split(split(request_url,'/')[10], '%%20')[1],
        split(request_url,'/')[4],
        split(request_url,'/')[6],
        split(request_url,'/')[9],
        split(request_url,'/')[3],
        count(*)
    FROM v2_raw_logs
    WHERE
        domain='addons.mozilla.org'
        and request_url like '/blocklist/3/%%'
        and ds=%s
    GROUP BY
        ds,
        split(request_url,'/')[5],
        split(split(request_url,'/')[10], '%%20')[0],
        split(split(request_url,'/')[10], '%%20')[1],
        split(request_url,'/')[4],
        split(request_url,'/')[6],
        split(request_url,'/')[9],
        split(request_url,'/')[3]
"""


@as_backfill_cron_app
@with_postgres_transactions()
@with_single_postgres_transaction()
class FetchADIFromHiveCronApp(BaseCronApp):
    """ This cron is our daily blocklist ping web logs query
        that rolls up all the browser checkins and let's us know
        how many browsers we think were active on the internet
        for a particular day """
    app_name = 'fetch-adi-from-hive'
    app_description = 'Fetch ADI From Hive App'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'query',
        default=_QUERY,
        doc='Hive query for fetching ADI data')

    required_config.add_option(
        'hive_host',
        default='localhost',
        doc='Hostname to run Hive query on')

    required_config.add_option(
        'hive_port',
        default=10000,
        doc='Port to run Hive query on')

    required_config.add_option(
        'hive_user',
        default='socorro',
        doc='User to connect to Hive with')

    required_config.add_option(
        'hive_password',
        default='ignored',
        doc='Password to connect to Hive with')

    required_config.add_option(
        'hive_database',
        default='default',
        doc='Database name to connect to Hive with')

    required_config.add_option(
        'hive_auth_mechanism',
        default='PLAIN',
        doc='Auth mechanism for Hive')

    def run(self, connection, date):
        target_date = (date - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        raw_adi_logs_pathname = os.path.join(
            tempfile.gettempdir(),
            "%s.raw_adi_logs.TEMPORARY%s" % (
                target_date,
                '.txt'
            )
        )
        try:
            with open(raw_adi_logs_pathname, 'w') as f:
                hive = pyhs2.connect(
                    host=self.config.hive_host,
                    port=self.config.hive_port,
                    authMechanism=self.config.hive_auth_mechanism,
                    user=self.config.hive_user,
                    password=self.config.hive_password,
                    database=self.config.hive_database
                )

                cur = hive.cursor()
                query = self.config.query % target_date
                cur.execute(query)
                for row in cur:
                    f.write("\t".join(str(v) for v in row))
                    f.write("\n")

            with open(raw_adi_logs_pathname, 'r') as f:
                pgcursor = connection.cursor()
                pgcursor.copy_from(
                    f,
                    'raw_adi_logs',
                    null='None',
                    columns=[
                        'report_date',
                        'product_name',
                        'product_os_platform',
                        'product_os_version',
                        'product_version',
                        'build',
                        'build_channel',
                        'product_guid',
                        'count'
                    ]
                )
        finally:
            if os.path.isfile(raw_adi_logs_pathname):
                os.remove(raw_adi_logs_pathname)

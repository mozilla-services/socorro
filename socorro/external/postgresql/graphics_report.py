# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common


logger = logging.getLogger("webapi")

"""
This was the original SQL used in the old cron job:


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

SQL = """
SELECT
    r.signature,
    NULL as url,        -- 1
    r.uuid as crash_id, -- 2
    NULL as client_crash_date,   -- 3
    to_char(r.date_processed,'YYYYMMDDHH24MI') as date_processed,         -- 4
    NULL as last_crash, -- 5
    r.product,    -- 6
    r.version,    -- 7
    r.build,      -- 8
    '' as branch, -- 9
    r.os_name,    --10
    r.os_version, --11
    r.cpu_name || ' | ' || r.cpu_info as cpu_info,   --12
    r.address,    --13
    ARRAY(SELECT 1 WHERE FALSE) as bug_list, --14
    NULL as user_comments, --15
    r.uptime as uptime_seconds, --16
    NULL as email, --17
    NULL as adu_count, --18
    r.topmost_filenames, --19
    NULL as addons_checked, --20
    NULL as flash_version, --21
    NULL as hangid, --22
    r.reason, --23
    NULL as process_type, --24
    r.app_notes, --25
    NULL as install_age, --26
    NULL as duplicate_of, --27
    r.release_channel as release_channel, --28
    NULL as productid --29
FROM
    reports r
WHERE
    r.date_processed BETWEEN %(date)s AND %(tomorrow)s
    AND
    r.product = %(product)s
ORDER BY 5 -- r.date_processed, munged
""".strip()


class GraphicsReport(PostgreSQLBase):
    """
    This implementation solves a un-legacy problem.
    We used to generate a big fat CSV file based on this query for
    the Mozilla Graphics team so that they can, in turn, analyze
    the data and produce pretty graphs that give them historic
    oversight of their efforts.
    See. http://people.mozilla.org/~bgirard/gfx_features_stats/

    This report might not be perfect but the intention is to have
    it as an postgres implementation so that it can satisfy their
    need and let the Socorro team avoid a complicated cron job
    that relies on dumping files to disk.
    """

    def get(self, **kwargs):
        filters = [
            ('date', datetime.datetime.utcnow().date(), 'date'),
            ('product', 'Firefox', 'str'),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        params['tomorrow'] = params['date'] + datetime.timedelta(days=1)
        results = self.query(SQL, params)
        hits = results.zipped()
        return {
            'hits': hits,
            'total': len(hits),
        }

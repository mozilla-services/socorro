# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common
from socorro.external import BadArgumentError


class Correlations(PostgreSQLBase):

    def get(self, **kwargs):
        filters = [
            ("report_date", None, "datetime"),
            ("report_type", None, "str"),
            ("product", None, "str"),
            ("version", None, "str"),
            ("signature", None, "str"),
            ("platform", None, "str"),
            ("min_crashes", 10, "int"),
            ("min_baseline_diff", 0.05, "float"),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        hits = []
        if params['report_type'] == 'interesting-addons':
            hits = self.interesting_addons(params)
        elif params['report_type'] == 'interesting-modules':
            hits = self.interesting_modules(params)
        elif params['report_type'] == 'interesting-addons-with-version':
            hits = self.interesting_addons_with_version(params)
        elif params['report_type'] == 'interesting-modules-with-version':
            hits = self.interesting_modules_with_version(params)
        elif params['report_type'] == 'core-counts':
            hits = self.core_counts(params)
        else:
            raise BadArgumentError(
                'report_type',
                received=report_type
            )

        return {
            'hits': hits,
            'total': len(hits)
        }

    def interesting_addons(self, params): 
        sql = """
        /* socorro.external.postgresql.correlations.Correlations.get(addons)*/
        WITH total_for_sig AS (
            SELECT
                sum(total)
            FROM correlations_addon
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
        ),
        total_for_os AS (
            SELECT
                sum(total)
            FROM correlations_addon
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
        ),
        crashes_for_sig AS (
            SELECT
                sum(total) AS crashes_for_sig,
                reason_id,
                addon_id
            FROM correlations_addon
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
            GROUP BY addon_id, reason_id
        ),
        crashes_for_os AS (
            SELECT
                sum(total) AS crashes_for_os,
                addon_id,
                reason_id
            FROM correlations_addon
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND os_name = %(platform)s
                AND product_name = %(product)s
                AND version_string = %(version)s
            GROUP BY addon_id, reason_id
        )
        SELECT
            (SELECT sum
             FROM total_for_sig) AS total_for_sig,
            (SELECT sum
             FROM total_for_os) AS total_for_os,
            crashes_for_sig,
            crashes_for_os,
            (crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float) * 100
             AS in_sig_ratio,
            (crashes_for_os::float / (SELECT sum FROM total_for_os)::float) * 100
             AS in_os_ratio,
            addon_id,
            reason
        FROM crashes_for_sig
        JOIN crashes_for_os USING (addon_id, reason_id)
        JOIN reasons USING (reason_id)
        WHERE crashes_for_sig >= %(min_crashes)s
        AND ((crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float)
             - (crashes_for_os::float / (SELECT sum FROM total_for_os)::float)
             >= %(min_baseline_diff)s)
        ;
        """

        error_message = ('Failed to retrieve correlations addon data ',
                         'from PostgreSQL')
        sql_results = self.query(sql, params, error_message=error_message)

        fields = (
                "total_for_sig",
                "total_for_os",
                "crashes_for_sig",
                "crashes_for_os",
                "in_sig_ratio",
                "in_os_ratio",
                "addon_id",
                "reason",
        )

        return [dict(zip(fields, row)) for row in sql_results]

    def interesting_modules(self, params):
        sql = """
        /* socorro.external.postgresql.correlations.Correlations.get(modules)*/
        WITH total_for_sig AS (
            SELECT
                sum(total)
            FROM correlations_module
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
        ),
        total_for_os AS (
            SELECT
                sum(total)
            FROM correlations_module
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
        ),
        crashes_for_sig AS (
            SELECT
                sum(total) AS crashes_for_sig,
                reason_id,
                module_id
            FROM correlations_module
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
            GROUP BY module_id, reason_id
        ),
        crashes_for_os AS (
            SELECT
                sum(total) AS crashes_for_os,
                module_id,
                reason_id
            FROM correlations_module
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND os_name = %(platform)s
                AND product_name = %(product)s
                AND version_string = %(version)s
            GROUP BY module_id, reason_id
        )
        SELECT
            (SELECT sum
             FROM total_for_sig) AS total_for_sig,
            (SELECT sum
             FROM total_for_os) AS total_for_os,
            crashes_for_sig,
            crashes_for_os,
            (crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float) * 100
             AS in_sig_ratio,
            (crashes_for_os::float / (SELECT sum FROM total_for_os)::float) * 100
             AS in_os_ratio,
            modules.name AS module_name,
            reason
        FROM crashes_for_sig
        JOIN crashes_for_os USING (module_id, reason_id)
        JOIN reasons USING (reason_id)
        JOIN modules USING (module_id)
        WHERE crashes_for_sig >= %(min_crashes)s
        AND ((crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float)
             - (crashes_for_os::float / (SELECT sum FROM total_for_os)::float)
             >= %(min_baseline_diff)s)
        ;
        """

        error_message = ('Failed to retrieve correlations addon data ',
                         'from PostgreSQL')
        sql_results = self.query(sql, params, error_message=error_message)

        fields = (
            "total_for_sig",
            "total_for_os",
            "crashes_for_sig",
            "crashes_for_os",
            "in_sig_ratio",
            "in_os_ratio",
            "module_name",
            "reason",
        )

        return [dict(zip(fields, row)) for row in sql_results]

    def interesting_addons_with_version(self, params):
        sql = """
        /* socorro.external.postgresql.correlations.Correlations.get(addons-version)*/
        WITH total_for_sig AS (
            SELECT
                sum(total)
            FROM correlations_addon
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
        ),
        total_for_os AS (
            SELECT
                sum(total)
            FROM correlations_addon
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
        ),
        crashes_for_sig AS (
            SELECT
                sum(total) AS crashes_for_sig,
                reason,
                addon_id,
                addon_version
            FROM correlations_addon
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
                JOIN reasons USING (reason_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
            GROUP BY reason, addon_id, addon_version
        ),
        crashes_for_os AS (
            SELECT
                sum(total) AS crashes_for_os,
                reason,
                addon_id,
                addon_version
            FROM correlations_addon
                JOIN product_versions USING (product_version_id)
                JOIN reasons USING (reason_id)
            WHERE report_date = %(report_date)s
                AND os_name = %(platform)s
                AND product_name = %(product)s
                AND version_string = %(version)s
            GROUP BY reason, addon_id, addon_version
        )
        SELECT
            (SELECT sum
             FROM total_for_sig) AS total_for_sig,
            (SELECT sum
             FROM total_for_os) AS total_for_os,
            crashes_for_sig,
            crashes_for_os,
            (crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float) * 100
             AS in_sig_ratio,
            (crashes_for_os::float / (SELECT sum FROM total_for_os)::float) * 100
             AS in_os_ratio,
            crashes_for_sig.addon_id,
            crashes_for_sig.addon_version,
            crashes_for_sig.reason
        FROM crashes_for_sig
        JOIN crashes_for_os USING (reason, addon_id, addon_version)
        WHERE crashes_for_sig >= %(min_crashes)s
        AND ((crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float)
             - (crashes_for_os::float / (SELECT sum FROM total_for_os)::float)
             >= %(min_baseline_diff)s)
        ;
        """

        error_message = ('Failed to retrieve correlations module data ',
                         'from PostgreSQL')
        sql_results = self.query(sql, params, error_message=error_message)

        fields = (
            "total_for_sig",
            "total_for_os",
            "crashes_for_sig",
            "crashes_for_os",
            "in_sig_ratio",
            "in_os_ratio",
            "addon_id",
            "addon_version",
            "reason",
        )

        return [dict(zip(fields, row)) for row in sql_results]

    def interesting_modules_with_version(self, params):
        sql = """
        /* socorro.external.postgresql.correlations.Correlations.get(modules-version)*/
        WITH total_for_sig AS (
            SELECT
                sum(total)
            FROM correlations_module
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
        ),
        total_for_os AS (
            SELECT
                sum(total)
            FROM correlations_module
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
        ),
        crashes_for_sig AS (
            SELECT
                sum(total) AS crashes_for_sig,
                reason_id,
                module_id
            FROM correlations_module
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
            GROUP BY reason_id, module_id
        ),
        crashes_for_os AS (
            SELECT
                sum(total) AS crashes_for_os,
                reason_id,
                module_id
            FROM correlations_module
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND os_name = %(platform)s
                AND product_name = %(product)s
                AND version_string = %(version)s
            GROUP BY reason_id, module_id
        )
        SELECT
            (SELECT sum
             FROM total_for_sig) AS total_for_sig,
            (SELECT sum
             FROM total_for_os) AS total_for_os,
            crashes_for_sig,
            crashes_for_os,
            (crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float) * 100
             AS in_sig_ratio,
            (crashes_for_os::float / (SELECT sum FROM total_for_os)::float) * 100
             AS in_os_ratio,
            name AS module_name,
            version AS module_version,
            reason
        FROM crashes_for_sig
        JOIN crashes_for_os USING (reason_id, module_id)
        JOIN modules USING (module_id)
        JOIN reasons USING (reason_id)
        WHERE crashes_for_sig >= %(min_crashes)s
        AND ((crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float)
             - (crashes_for_os::float / (SELECT sum FROM total_for_os)::float)
             >= %(min_baseline_diff)s)
        ;
        """

        error_message = ('Failed to retrieve correlations module data ',
                         'from PostgreSQL')
        sql_results = self.query(sql, params, error_message=error_message)

        fields = (
            "total_for_sig",
            "total_for_os",
            "crashes_for_sig",
            "crashes_for_os",
            "in_sig_ratio",
            "in_os_ratio",
            "module_name",
            "module_version",
            "reason",
        )

        return [dict(zip(fields, row)) for row in sql_results]

    def core_counts(self, params):
        sql = """
        /* socorro.external.postgresql.correlations.Correlations.get(cores)*/
        WITH total_for_sig AS (
            SELECT
                sum(total)
            FROM correlations_core
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
        ),
        total_for_os AS (
            SELECT
                sum(total)
            FROM correlations_core
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
        ),
        crashes_for_sig AS (
            SELECT
                sum(total) AS crashes_for_sig,
                reason,
                cpu_arch,
                cpu_count
            FROM correlations_core
                JOIN product_versions USING (product_version_id)
                JOIN signatures USING (signature_id)
                JOIN reasons USING (reason_id)
            WHERE report_date = %(report_date)s
                AND product_name = %(product)s
                AND os_name = %(platform)s
                AND version_string = %(version)s
                AND signature = %(signature)s
            GROUP BY cpu_arch, cpu_count, reason
        ),
        crashes_for_os AS (
            SELECT
                sum(total) AS crashes_for_os,
                cpu_arch,
                cpu_count
            FROM correlations_core
                JOIN product_versions USING (product_version_id)
            WHERE report_date = %(report_date)s
                AND os_name = %(platform)s
                AND product_name = %(product)s
                AND version_string = %(version)s
            GROUP BY cpu_arch, cpu_count
        )
        SELECT
            (SELECT sum
             FROM total_for_sig) AS total_for_sig,
            (SELECT sum
             FROM total_for_os) AS total_for_os,
            crashes_for_sig,
            crashes_for_os,
            (crashes_for_sig::float / (SELECT sum FROM total_for_sig)::float) * 100
             AS in_sig_ratio,
            (crashes_for_os::float / (SELECT sum FROM total_for_os)::float) * 100
             AS in_os_ratio,
            cpu_arch,
            cpu_count,
            reason
        FROM crashes_for_sig
        JOIN crashes_for_os USING (cpu_arch, cpu_count)
        WHERE crashes_for_sig >= %(min_crashes)s
        ;
        """

        error_message = ('Failed to retrieve correlations core data ',
                         'from PostgreSQL')
        sql_results = self.query(sql, params, error_message=error_message)

        fields = (
            "total_for_sig",
            "total_for_os",
            "crashes_for_sig",
            "crashes_for_os",
            "in_sig_ratio",
            "in_os_ratio",
            "cpu_arch",
            "cpu_count",
            "reason",
        )

        return [dict(zip(fields, row)) for row in sql_results]

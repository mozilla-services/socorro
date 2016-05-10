# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import datetime

import ujson as json

from configman.converters import class_converter, str_to_list

from socorro.external.postgresql.base import PostgreSQLBase
from socorrolib.lib import datetimeutil, external_common, BadArgumentError

from socorro.analysis.correlations.correlations_rule_base import (
    CorrelationsStorageBase,
)
from socorro.external.postgresql.dbapi2_util import (
    # SQLDidNotReturnSingleValue,
    # single_value_sql,
    execute_no_results
)


class SignatureNotFoundError(Exception):
    """when we encounter a signature that we don't have in the database"""


class ReasonNotFoundError(Exception):
    """when we encounter a reason that we don't have in the database"""


from configman import Namespace, RequiredConfig, class_converter

class Correlations(CorrelationsStorageBase, PostgreSQLBase):

    required_config = Namespace()
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutor",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )
    required_config.add_option(
        'database_class',
        default=(
            'socorro.external.postgresql.connection_context'
            '.ConnectionContext'
        ),
        doc='the class responsible for connecting to Postgres',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql',
    )

    required_config.add_option(
        'recognized_platforms',
        default='Windows NT, Linux, Mac OS X',
        doc='The kinds of platform names we recognize',
        from_string_converter=str_to_list,
    )

    def __init__(self, config):
        super(Correlations, self).__init__(config)
        PostgreSQLBase.__init__(self, config=self.config)

    def get(self, **kwargs):
        raise NotImplementedError

    def _prefix_to_datetime_date(self, prefix):
        yy = int(prefix[:4])
        mm = int(prefix[4:6])
        dd = int(prefix[6:8])
        return datetime.date(yy, mm, dd)

    @staticmethod
    def _split_signature_and_reason(signature_and_reason):
        return signature_and_reason.rsplit('__reason__', 1)

    def _upsert_correlation(
        self,
        connection, # XXX really?
        product,
        version,
        reason,
        signature,
        platform,
        key,
        count,
        notes,
        date,
        payload
    ):
        # Upsert
        sql = """
        WITH
        update_correlation AS (
            UPDATE correlations SET
                count = %(count)s,
                notes = %(notes)s,
                payload = %(payload)s
            WHERE
                product_version_id = %(product_version_id)s AND
                platform = %(platform)s AND
                key = %(key)s AND
                date = %(date)s AND
                signature_id = %(signature_id)s AND
                reason_id = %(reason_id)s
            RETURNING 1
        ),
        insert_correlation AS (
            INSERT INTO correlations (
                product_version_id,
                platform,
                key,
                date,
                signature_id,
                reason_id,
                count,
                notes,
                payload
            ) (
                SELECT
                    %(product_version_id)s AS product_version_id,
                    %(platform)s AS platform,
                    %(key)s AS key,
                    %(date)s AS date,
                    %(signature_id)s AS signature_id,
                    %(reason_id)s AS reason_id,
                    %(count)s AS count,
                    %(notes)s AS notes,
                    %(payload)s AS payload
                WHERE NOT EXISTS (
                    SELECT
                        product_version_id
                    FROM
                        correlations
                    WHERE
                        product_version_id = %(product_version_id)s AND
                        platform = %(platform)s AND
                        key = %(key)s AND
                        date = %(date)s AND
                        signature_id = %(signature_id)s AND
                        reason_id = %(reason_id)s
                    LIMIT 1
                )
            )
            RETURNING 2
        )
        SELECT * FROM update_correlation
        UNION ALL
        SELECT * FROM insert_correlation
        """
        execute_no_results(
            connection,
            sql,
            {
                'product_version_id': self.get_product_version_id(
                    connection,
                    product,
                    version
                ),
                'platform': platform,
                'signature_id': self.get_signature_id(connection, signature),
                'reason_id': self.get_reason_id(connection, reason),
                'key': key,
                'count': count,
                'notes': notes,
                'date': date,
                'payload': json.dumps(payload)
            },
        )

    product_version_ids = {}  # cache

    def get_product_version_id(self, connection, product, version):
        key = (product, version)
        if key not in self.product_version_ids:
            sql = """
                SELECT
                    product_version_id
                FROM product_versions
                WHERE
                    product_name = %(product_name)s AND
                    version_string = %(version_string)s
            """
            result, = self.query(
                sql,
                {
                    'product_name': product,
                    'version_string': version
                },
                connection=connection
            )
            product_version_id, = result
            self.product_version_ids[key] = product_version_id
        return self.product_version_ids[key]


    signature_ids = {}  # cache

    def get_signature_id(self, connection, signature):
        if signature not in self.signature_ids:
            sql = """
                SELECT
                    signature_id
                FROM signatures
                WHERE
                    signature = %(signature)s
            """
            try:
                result, = self.query(
                    sql,
                    {
                        'signature': signature,
                    },
                    connection=connection
                )
                signature_id, = result
            except ValueError:
                raise SignatureNotFoundError(signature)
            self.signature_ids[signature] = signature_id

        return self.signature_ids[signature]

    reason_ids = {}  # cache

    def get_reason_id(self, connection, reason):
        if reason not in self.reason_ids:
            sql = """
                SELECT
                    reason_id
                FROM reason
                WHERE
                    reason = %(reason)s
            """
            try:
                result, = self.query(
                    sql,
                    {
                        'reason': reason,
                    },
                    connection=connection
                )
                reason_id, = result
            except ValueError:
                # XXX Perhaps we need to create the row here
                raise ReasonNotFoundError(signature)
            self.reason_ids[reason] = reason_id

        return self.reason_ids[reason]

    def close(self):
        """for the benefit of this class's subclasses that need to have
        this defined."""
        pass



class CoreCounts(Correlations):

    def store(
        self,
        counts_summary_structure,
        prefix,
        name,
        key,
    ):
        date = self._prefix_to_datetime_date(prefix)

        notes = counts_summary_structure['notes']
        product = key.split('_', 1)[0]
        version = key.split('_', 1)[1]

        with self.get_connection() as connection:

            for platform in counts_summary_structure:
                if platform not in self.config.recognized_platforms:
                    continue
                count = counts_summary_structure[platform]['count']
                signatures = counts_summary_structure[platform]['signatures']

                for signature_and_reason, payload in signatures.items():
                    signature, reason = self._split_signature_and_reason(
                        signature_and_reason
                    )
                    try:
                        self._upsert_correlation(
                            connection,
                            product,
                            version,
                            signature,
                            reason,
                            platform,
                            name,
                            count,
                            notes,
                            date,
                            payload,
                        )
                    except SignatureNotFoundError as exp:
                        self.config.logger.warning(
                            'Not a recognized signature %r',
                            exp
                        )


class InterestingModules(Correlations):

    def store(
        self,
        counts_summary_structure,
        prefix,
        name,
        key,
    ):
        date = self._prefix_to_datetime_date(prefix)

        notes = counts_summary_structure['notes']
        product = key.split('_', 1)[0]
        version = key.split('_', 1)[1]
        os_counters = counts_summary_structure['os_counters']
        with self.get_connection() as connection:
            for platform in os_counters:
                if not platform:
                    continue
                if platform not in self.config.recognized_platforms:
                    continue
                count = os_counters[platform]['count']
                signatures = os_counters[platform]['signatures']

                for signature_and_reason, payload in signatures.items():
                    signature, reason = self._split_signature_and_reason(
                        signature_and_reason
                    )
                    try:
                        self._upsert_correlation(
                            connection,
                            product,
                            version,
                            signature,
                            reason,
                            platform,
                            name,
                            count,
                            notes,
                            date,
                            payload,
                        )
                    except SignatureNotFoundError as exp:
                        self.config.logger.warning(
                            'Not a recognized signature %r',
                            exp
                        )

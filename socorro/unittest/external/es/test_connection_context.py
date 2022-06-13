# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime

from socorro.lib.libdatetime import utc_now

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


class TestConnectionContext:
    def test_create_index(self, es_conn):
        # Delete any existing indices first
        for index in es_conn.get_indices():
            es_conn.delete_index(index)
        es_conn.refresh()
        es_conn.health_check()

        template = es_conn.get_index_template()
        now = utc_now()
        index_name = now.strftime(template)

        # Create the index and make sure it's there
        es_conn.create_index(index_name)
        es_conn.health_check()
        assert index_name in list(es_conn.get_indices())

    def test_delete_index(self, es_conn):
        template = es_conn.get_index_template()
        now = utc_now()
        index_name = now.strftime(template)

        es_conn.create_index(index_name)
        es_conn.health_check()
        assert index_name in list(es_conn.get_indices())

        es_conn.delete_index(index_name)
        assert index_name not in list(es_conn.get_indices())

    def test_delete_old_indices(self, es_conn):
        # Delete any existing indices first
        for index in es_conn.get_indices():
            es_conn.delete_index(index)
        es_conn.refresh()
        es_conn.health_check()

        # Create an index > retention_policy
        template = es_conn.get_index_template()
        now = utc_now()
        current_index_name = now.strftime(template)
        before_retention_policy = now - datetime.timedelta(
            weeks=es_conn.config.retention_policy
        )
        old_index_name = before_retention_policy.strftime(template)

        es_conn.create_index(current_index_name)
        es_conn.create_index(old_index_name)
        es_conn.health_check()
        assert list(es_conn.get_indices()) == [old_index_name, current_index_name]

        # Now delete all expired indices and make sure current is still there
        es_conn.delete_expired_indices()
        es_conn.health_check()
        assert list(es_conn.get_indices()) == [current_index_name]

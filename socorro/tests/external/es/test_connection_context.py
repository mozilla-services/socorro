# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro import settings
from socorro.libclass import build_instance
from socorro.lib.libdatetime import utc_now


class TestConnectionContext:
    def build_conn(self):
        return build_instance(
            class_path="socorro.external.es.connection_context.ConnectionContext",
            kwargs=settings.CRASH_DESTINATIONS["es"]["options"],
        )

    def test_create_index(self, es_helper):
        # Delete any existing indices first
        es_helper.delete_indices()

        es_helper.refresh()
        es_helper.health_check()

        template = es_helper.get_index_template()
        now = utc_now()
        index_name = now.strftime(template)

        conn = self.build_conn()

        # Create an index
        index_settings = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                },
            },
        }
        conn.create_index(index_name=index_name, index_settings=index_settings)
        conn.health_check()
        assert index_name in list(es_helper.get_indices())

    def test_delete_index(self, es_helper):
        template = es_helper.get_index_template()
        now = utc_now()
        index_name = now.strftime(template)

        conn = self.build_conn()

        # Create an index and assert it's there
        index_settings = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                },
            },
        }
        conn.create_index(index_name=index_name, index_settings=index_settings)
        conn.health_check()
        assert index_name in list(es_helper.get_indices())

        # Delete the index and assert it's no longer there
        conn.delete_index(index_name)
        assert index_name not in list(es_helper.get_indices())

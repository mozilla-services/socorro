# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro import settings
from socorro.libclass import build_instance
from socorro.lib.libdatetime import utc_now


class TestLegacyConnectionContext:
    def build_conn(self):
        return build_instance(
            class_path="socorro.external.legacy_es.connection_context.LegacyConnectionContext",
            kwargs=settings.LEGACY_ES_STORAGE["options"],
        )

    def test_create_index(self, legacy_es_helper):
        # Delete any existing indices first
        legacy_es_helper.delete_indices()

        legacy_es_helper.refresh()
        legacy_es_helper.health_check()

        template = legacy_es_helper.get_index_template()
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
        assert index_name in list(legacy_es_helper.get_indices())

    def test_delete_index(self, legacy_es_helper):
        template = legacy_es_helper.get_index_template()
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
        assert index_name in list(legacy_es_helper.get_indices())

        # Delete the index and assert it's no longer there
        conn.delete_index(index_name)
        assert index_name not in list(legacy_es_helper.get_indices())

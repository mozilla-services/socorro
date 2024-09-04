# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro import settings
from socorro.external.legacy_es.super_search_fields import FIELDS
from socorro.external.legacy_es.supersearch import LegacySuperSearch
from socorro.lib.libdatetime import utc_now
from socorro.libclass import build_instance_from_settings
from socorro.lib.libooid import create_new_ooid


class TestIntegrationAnalyzers:
    """Test the custom analyzers we create in our indices"""

    def build_crashstorage(self):
        return build_instance_from_settings(settings.LEGACY_ES_STORAGE)

    def test_semicolon_keywords(self, es_helper):
        """Test the analyzer called `semicolon_keywords`.

        That analyzer creates tokens (terms) by splitting the input on
        semicolons (;) only.

        """
        crashstorage = self.build_crashstorage()
        api = LegacySuperSearch(crashstorage=crashstorage)
        now = utc_now()
        crash_id_1 = create_new_ooid()
        crash_id_2 = create_new_ooid()

        value1 = "/path/to/dll;;foo;C:\\bar\\boo"
        es_helper.index_crash(
            processed_crash={
                "uuid": crash_id_1,
                "app_init_dlls": value1,
                "date_processed": now,
            },
        )
        value2 = "/path/to/dll;D:\\bar\\boo"
        es_helper.index_crash(
            processed_crash={
                "uuid": crash_id_2,
                "app_init_dlls": value2,
                "date_processed": now,
            },
        )
        es_helper.refresh()

        res = api.get(
            app_init_dlls="/path/to/dll", _facets=["app_init_dlls"], _fields=FIELDS
        )
        assert res["total"] == 2
        assert "app_init_dlls" in res["facets"]
        facet_terms = [x["term"] for x in res["facets"]["app_init_dlls"]]
        assert "/path/to/dll" in facet_terms
        assert "c:\\bar\\boo" in facet_terms
        assert "foo" in facet_terms

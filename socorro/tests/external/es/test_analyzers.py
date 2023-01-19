# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro.lib import libdatetime
from socorro.external.es.super_search_fields import FIELDS
from socorro.external.es.supersearch import SuperSearch
from socorro.tests.external.es.base import ElasticsearchTestCase


# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


class TestIntegrationAnalyzers(ElasticsearchTestCase):
    """Test the custom analyzers we create in our indices"""

    def setup_method(self):
        super().setup_method()

        config = self.get_base_config(cls=SuperSearch)
        self.api = SuperSearch(config=config)
        self.now = libdatetime.utc_now()

    def test_semicolon_keywords(self):
        """Test the analyzer called `semicolon_keywords`.

        That analyzer creates tokens (terms) by splitting the input on
        semicolons (;) only.

        """
        value1 = "/path/to/dll;;foo;C:\\bar\\boo"
        self.index_crash(
            processed_crash={"app_init_dlls": value1, "date_processed": self.now},
            raw_crash={},
        )
        value2 = "/path/to/dll;D:\\bar\\boo"
        self.index_crash(
            processed_crash={"app_init_dlls": value2, "date_processed": self.now},
            raw_crash={},
        )
        self.es_context.refresh()

        res = self.api.get(
            app_init_dlls="/path/to/dll", _facets=["app_init_dlls"], _fields=FIELDS
        )
        assert res["total"] == 2
        assert "app_init_dlls" in res["facets"]
        facet_terms = [x["term"] for x in res["facets"]["app_init_dlls"]]
        assert "/path/to/dll" in facet_terms
        assert "c:\\bar\\boo" in facet_terms
        assert "foo" in facet_terms

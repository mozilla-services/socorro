# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
from distutils.version import LooseVersion
from functools import wraps
import random
import uuid

from configman import ConfigurationManager, environment
from elasticsearch.helpers import bulk
import pytest

from socorro.external.es.connection_context import ConnectionContext
from socorro.external.es.supersearch import SuperSearch
from socorro.external.es.super_search_fields import FIELDS


DEFAULT_VALUES = {
    "resource.elasticsearch.elasticsearch_index": ("socorro_integration_test_reports"),
    "resource.elasticsearch.elasticsearch_timeout": 10,
}


CRON_JOB_EXTA_VALUES = {"resource.elasticsearch.backoff_delays": [1]}


def minimum_es_version(minimum_version):
    """Skip the test if the Elasticsearch version is less than specified

    :arg minimum_version: string; the minimum Elasticsearch version required

    """

    def decorated(test):
        """Decorator to only run the test if ES version is greater or equal than specified"""

        @wraps(test)
        def test_with_version(self):
            """Only run the test if ES version is not less than specified"""
            actual_version = self.connection.info()["version"]["number"]
            if LooseVersion(actual_version) >= LooseVersion(minimum_version):
                test(self)
            else:
                pytest.skip()

        return test_with_version

    return decorated


class SuperSearchWithFields(SuperSearch):
    """Convenience class for SuperSearch to pass all fields

    SuperSearch's get method requires to be passed the list of all fields. This
    class does that automatically so we can just use ``get()``.

    """

    def get(self, **kwargs):
        kwargs["_fields"] = copy.deepcopy(FIELDS)
        return super().get(**kwargs)


class TestCaseWithConfig:
    """A simple TestCase class that can create configuration objects"""

    def setup_method(self, method):
        pass

    def teardown_method(self, method):
        pass

    def get_tuned_config(self, sources, extra_values=None):
        if not isinstance(sources, (list, tuple)):
            sources = [sources]

        config_definitions = []
        for source in sources:
            conf = source.get_required_config()
            config_definitions.append(conf)

        values_source = {}
        if extra_values:
            values_source.update(extra_values)

        config_manager = ConfigurationManager(
            config_definitions,
            app_name="testapp",
            app_version="1.0",
            app_description="Elasticsearch integration tests",
            values_source_list=[environment, values_source],
            argv_source=[],
        )

        return config_manager.get_config()


class ElasticsearchTestCase(TestCaseWithConfig):
    """Base class for Elastic Search related unit tests"""

    def setup_method(self, method):
        super().setup_method(method)
        self.config = self.get_base_config()
        self.es_context = ConnectionContext(self.config)

        self.index_client = self.es_context.indices_client()

        with self.es_context() as conn:
            self.connection = conn

        self.es_context.create_index(self.es_context.get_index_template())

    def teardown_method(self, method):
        # Clear the test indices.
        self.index_client.delete(self.es_context.get_index_template())
        super().teardown_method(method)

    def health_check(self):
        self.connection.cluster.health(wait_for_status="yellow", request_timeout=5)

    def get_url(self):
        """Returns the first url in the elasticsearch_urls list"""
        return self.config.elasticsearch_urls[0]

    def get_tuned_config(self, sources, extra_values=None):
        values_source = DEFAULT_VALUES.copy()
        if extra_values:
            values_source.update(extra_values)

        return super().get_tuned_config(sources, values_source)

    def get_base_config(self, cls=ConnectionContext, es_index=None):
        extra_values = None
        if es_index:
            extra_values = {"resource.elasticsearch.elasticsearch_index": es_index}

        return self.get_tuned_config(cls, extra_values=extra_values)

    def index_crash(self, processed_crash=None, raw_crash=None, crash_id=None):
        if crash_id is None:
            crash_id = str(uuid.UUID(int=random.getrandbits(128)))

        raw_crash = raw_crash or {}
        processed_crash = processed_crash or {}

        doc = {
            "crash_id": crash_id,
            "processed_crash": processed_crash,
            "raw_crash": raw_crash,
        }
        index_name = self.es_context.get_index_template()
        res = self.connection.index(
            index=index_name,
            doc_type=self.es_context.get_doctype(),
            id=crash_id,
            body=doc,
        )
        return res["_id"]

    def index_many_crashes(
        self, number, processed_crash=None, raw_crash=None, loop_field=None
    ):
        processed_crash = processed_crash or {}
        raw_crash = raw_crash or {}

        actions = []
        for i in range(number):
            crash_id = str(uuid.UUID(int=random.getrandbits(128)))

            if loop_field is not None:
                processed_copy = processed_crash.copy()
                processed_copy[loop_field] = processed_crash[loop_field] % i
            else:
                processed_copy = processed_crash

            doc = {
                "crash_id": crash_id,
                "processed_crash": processed_copy,
                "raw_crash": raw_crash,
            }
            action = {
                "_index": self.es_context.get_index_template(),
                "_type": self.es_context.get_doctype(),
                "_id": crash_id,
                "_source": doc,
            }
            actions.append(action)

        bulk(client=self.connection, actions=actions)
        self.es_context.refresh()

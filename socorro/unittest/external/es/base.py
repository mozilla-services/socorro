# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import timedelta
from distutils.version import LooseVersion
from functools import wraps
import random
import uuid

from configman import ConfigurationManager, environment
import pytest

from socorro.external.es.connection_context import ConnectionContext
from socorro.external.es.crashstorage import ESCrashStorage
from socorro.lib.libdatetime import utc_now


DEFAULT_VALUES = {
    "resource.elasticsearch.elasticsearch_index": "testsocorro_%W",
    "resource.elasticsearch.elasticsearch_index_regex": "^testsocorro.*$",
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
            actual_version = self.conn.info()["version"]["number"]
            if LooseVersion(actual_version) >= LooseVersion(minimum_version):
                test(self)
            else:
                pytest.skip()

        return test_with_version

    return decorated


class TestCaseWithConfig:
    """A simple TestCase class that can create configuration objects"""

    def setup_method(self):
        pass

    def teardown_method(self):
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

    def setup_method(self):
        super().setup_method()
        self.config = self.get_base_config()
        self.es_context = ConnectionContext(self.config)
        self.crashstorage = ESCrashStorage(config=self.get_tuned_config(ESCrashStorage))

        self.index_client = self.es_context.indices_client()
        self.conn = self.es_context.connection()

        # Delete everything there first
        for index_name in self.es_context.get_indices():
            print(f"setup: delete test index: {index_name}")
            self.es_context.delete_index(index_name)

        # Create all the indexes for the last couple of weeks; we have to do it this way
        # to handle split indexes over the new year
        to_create = set()
        for i in range(14):
            index_name = self.es_context.get_index_for_date(
                utc_now() - timedelta(days=i)
            )
            to_create.add(index_name)

        for index_name in to_create:
            print(f"setup: creating index: {index_name}")
            self.es_context.create_index(index_name)

    def teardown_method(self):
        for index_name in self.es_context.get_indices():
            print(f"teardown: delete test index: {index_name}")
            self.es_context.delete_index(index_name)
        super().teardown_method()

    def health_check(self):
        self.conn.cluster.health(wait_for_status="yellow", request_timeout=5)

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

    def index_crash(
        self, processed_crash=None, raw_crash=None, crash_id=None, refresh=True
    ):
        """Index a single crash and refresh"""
        if crash_id is None:
            crash_id = str(uuid.UUID(int=random.getrandbits(128)))

        raw_crash = raw_crash or {}
        processed_crash = processed_crash or {}
        raw_crash["uuid"] = crash_id
        processed_crash["crash_id"] = crash_id
        processed_crash["uuid"] = crash_id

        self.crashstorage.save_processed_crash(raw_crash, processed_crash)

        if refresh:
            self.es_context.refresh()

        return crash_id

    def index_many_crashes(
        self, number, processed_crash=None, raw_crash=None, loop_field=None
    ):
        """Index multiple crashes and refresh at the end"""
        processed_crash = processed_crash or {}
        raw_crash = raw_crash or {}

        crash_ids = []
        for i in range(number):
            if loop_field is not None:
                processed_copy = processed_crash.copy()
                processed_copy[loop_field] = processed_crash[loop_field] % i
            else:
                processed_copy = processed_crash

            crash_ids.append(
                self.index_crash(
                    raw_crash=raw_crash, processed_crash=processed_copy, refresh=False
                )
            )

        self.es_context.refresh()
        return crash_ids

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import os
import hashlib

from configman import Namespace
from configman.converters import class_converter, str_to_list

from socorro.analysis.correlations.correlations_rule_base import (
    CorrelationsStorageBase,
)


# Needed for the ability to find the
# mappings/correlations_index_settings.json file whose path is relative
# to this file.
HERE = os.path.dirname(os.path.abspath(__file__))


class Correlations(CorrelationsStorageBase):

    required_config = Namespace()

    required_config.elasticsearch = Namespace()
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.elasticsearch',
    )

    required_config.add_option(
        'index_creator',
        default='socorro.external.es.index_creator.IndexCreator',
        from_string_converter=class_converter,
        doc='a class that can create Elasticsearch indices',
    )
    required_config.add_option(
        'elasticsearch_correlations_index_settings',
        default='%s/mappings/correlations_index_settings.json' % HERE,
        doc='the file containing the mapping of the indexes receiving '
            'correlations data',
    )
    required_config.add_option(
        'elasticsearch_correlations_index',
        default='socorro_correlations_%Y%m',
        doc='the index that handles data about correlations',
    )

    required_config.add_option(
        'recognized_platforms',
        default='Windows NT, Linux, Mac OS X',
        doc='The kinds of platform names we recognize',
        from_string_converter=str_to_list,
    )

    def __init__(self, config):
        super(Correlations, self).__init__(config)
        self.config = config

        self.es_context = self.config.elasticsearch.elasticsearch_class(
            config=self.config.elasticsearch
        )

        self.indices_cache = set()

    def get_index_for_date(self, date):
        return date.strftime(self.config.elasticsearch_correlations_index)

    def create_correlations_index(self, es_index):
        """Create an index to store correlations. """
        if es_index not in self.indices_cache:
            settings_json = open(
                self.config.elasticsearch_correlations_index_settings
            ).read()
            es_settings = json.loads(settings_json)

            index_creator = self.config.index_creator(self.config)
            # This is resilient to being called repeatedly even
            # when the index already exists.
            index_creator.create_index(es_index, es_settings)
            self.indices_cache.add(es_index)

    def _prefix_to_datetime_date(self, prefix):
        yy = int(prefix[:4])
        mm = int(prefix[4:6])
        dd = int(prefix[6:8])
        return datetime.date(yy, mm, dd)

    @staticmethod
    def make_id(document, only_keys=None):
        only_keys = only_keys or (
            'platform',
            'product',
            'version',
            'date',
            'key',
            'signature',
        )

        string_parts = []
        for key, value in sorted(document.items()):
            if key not in only_keys:
                continue
            if isinstance(value, datetime.date):
                value = value.isoformat()
            if isinstance(value, int):
                value = str(value)
            if isinstance(value, basestring):
                string_parts.append(value)
        return hashlib.md5(
            (''.join(string_parts)).encode('utf-8')
        ).hexdigest()

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
        index = self.get_index_for_date(date)
        self.create_correlations_index(index)

        notes = counts_summary_structure['notes']
        product = key.split('_', 1)[0]
        version = key.split('_', 1)[1]

        for platform in counts_summary_structure:
            if platform not in self.config.recognized_platforms:
                continue
            count = counts_summary_structure[platform]['count']
            signatures = counts_summary_structure[platform]['signatures']

            for signature, payload in signatures.items():
                doc = {
                    'platform': platform,
                    'product': product,
                    'version': version,
                    'count': count,
                    'signature': signature,
                    'payload': json.dumps(payload),
                    'date': date,
                    'key': name,
                    'notes': notes,
                }
                with self.es_context() as conn:
                    conn.index(
                        index=index,
                        # see correlations_index_settings.json
                        doc_type='correlations',
                        body=doc,
                        id=self.make_id(doc)
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
        index = self.get_index_for_date(date)
        self.create_correlations_index(index)

        notes = counts_summary_structure['notes']
        product = key.split('_', 1)[0]
        version = key.split('_', 1)[1]
        os_counters = counts_summary_structure['os_counters']
        for platform in os_counters:
            if not platform:
                continue
            if platform not in self.config.recognized_platforms:
                continue
            count = os_counters[platform]['count']
            signatures = os_counters[platform]['signatures']

            for signature, payload in signatures.items():
                doc = {
                    'platform': platform,
                    'product': product,
                    'version': version,
                    'count': count,
                    'signature': signature,
                    'payload': json.dumps(payload),
                    'date': date,
                    'key': name,
                    'notes': notes,
                }
                with self.es_context() as conn:
                    conn.index(
                        index=index,
                        # see correlations_index_settings.json
                        doc_type='correlations',
                        body=doc,
                        id=self.make_id(doc)
                    )

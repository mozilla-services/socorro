# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os

from configman import Namespace, RequiredConfig
from configman.converters import class_converter


HERE = os.path.dirname(os.path.abspath(__file__))


class Correlations(RequiredConfig):

    required_config = Namespace()
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

    def __init__(self, config):
        super(Correlations, self).__init__()
        self.config = config

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
            index_creator.create_index(es_index, es_settings)

            self.indices_cache.add(es_index)

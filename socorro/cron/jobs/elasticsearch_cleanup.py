# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from configman import Namespace
from configman.converters import class_converter

from socorro.cron.base import BaseCronApp


logger = logging.getLogger(__name__)


class ElasticsearchCleanupCronApp(BaseCronApp):
    """Delete old Elasticsearch indices."""

    app_name = 'elasticsearch-cleanup'
    app_version = '1.0'
    app_description = 'Delete old Elasticsearch indices'

    required_config = Namespace()
    required_config.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        doc='connection context class',
        from_string_converter=class_converter,
    )

    def run(self):
        conn = self.config.elasticsearch_class(self.config)
        for index in conn.delete_expired_indices():
            logger.info('Deleting %s', index)

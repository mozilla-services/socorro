#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from configman import Namespace, class_converter

from socorro.app.socorro_app import App


FAIL = 1
SUCCESS = 0


class ClearESIndicesApp(App):
    """Deletes all week-based crash indices in Elasticsearch.
    """
    app_name = 'clear_es_indices'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()
    required_config.add_option(
        'elasticsearch_cleaner_class',
        default='socorro.external.es.index_cleaner.IndexCleaner',
        doc='a class that handles the deletion of obsolete indices',
        from_string_converter=class_converter,
    )

    def main(self):
        cleaner = self.config.elasticsearch_cleaner_class(self.config)
        deleted_indices = cleaner.delete_indices()
        for index in deleted_indices:
            self.config.logger.info('Deleted elasticsearch index %s' % (index,))
        return SUCCESS


if __name__ == '__main__':
    sys.exit(ClearESIndicesApp.run())

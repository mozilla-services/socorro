# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from elasticsearch import helpers
from configman import Namespace, RequiredConfig, class_converter


class ESNewCrashSource(RequiredConfig):

    required_config = Namespace()
    required_config.add_option(
        'cap',
        default=0,
        doc='If set to something other than 0, caps how many to yield'
    )
    required_config.elasticsearch = Namespace()
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.elasticsearch',
    )

    def __init__(self, config, name=None, quit_check_callback=None):
        self.config = config
        self.es_context = self.config.elasticsearch.elasticsearch_class(
            config=self.config.elasticsearch
        )

    def new_crashes(self, date, product, versions):
        """Return an iterator of crash IDs.

        Confusingly, inside this method we're using an iterator.
        The reason we first exhaust the iterator BEFORE returning it
        is because *if* we do this:

            res = helpers.scan(...)
            for hit in res:
                yield hit['fields']['crash_id'][0]

        Then, between each of these yields the fetch transform save
        app will do something with this crash ID. That's cute but the
        problem is that if you get 1,000 crash IDs out and between each
        1,000 you have to do a S3 boto get, you have to wait many
        milliseconds between each and then the scroll connection
        has to stay open too long.

        Instead, we get all the crash IDs out first, and *then* return
        an iterator.
        """
        next_day = date + datetime.timedelta(days=1)

        query = {
            'filter': {
                'bool': {
                    'must': [
                        {
                            'range': {
                                'processed_crash.date_processed': {
                                    'gte': date.isoformat(),
                                    'lt': next_day.isoformat(),
                                }
                            }
                        },
                        {
                            'term': {
                                'processed_crash.product': product.lower()
                            }
                        },
                        {
                            'terms': {
                                'processed_crash.version': [
                                    x.lower() for x in versions
                                ]
                            }
                        }
                    ]
                }
            }
        }

        es_index = date.strftime(self.config.elasticsearch.elasticsearch_index)
        es_doctype = self.config.elasticsearch.elasticsearch_doctype

        crash_ids = []
        with self.es_context() as es_context:
            res = helpers.scan(
                es_context,
                scroll='2m',  # keep the "scroll" connection open for 2 minutes
                index=es_index,
                doc_type=es_doctype,
                fields=['crash_id'],
                query=query,
            )
            for hit in res:
                crash_ids.append(hit['fields']['crash_id'][0])
                if self.config.cap and len(crash_ids) >= self.config.cap:
                    break

        return iter(crash_ids)

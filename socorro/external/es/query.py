# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import elasticsearch
import json
import re

from configman import RequiredConfig, Namespace, class_converter

from socorro.lib import DatabaseError, MissingArgumentError, ResourceNotFound
from socorro.external.es.base import generate_list_of_indexes
from socorro.external.es.supersearch import BAD_INDEX_REGEX
from socorro.lib import libdatetime, external_common


class Query(RequiredConfig):
    """Implement the /query service with ElasticSearch."""

    required_config = Namespace()
    required_config.add_option(
        "elasticsearch_class",
        doc="a class that implements the ES connection object",
        default="socorro.external.es.connection_context.ConnectionContext",
        from_string_converter=class_converter,
    )

    filters = [("query", None, "json"), ("indices", None, ["list", "str"])]

    def __init__(self, config):
        self.config = config
        self.context = self.config.elasticsearch_class(self.config)

    def get_connection(self):
        with self.context(timeout=self.context.get_timeout_extended()) as conn:
            return conn

    def get(self, **kwargs):
        """Return the result of a custom query"""
        params = external_common.parse_arguments(self.filters, kwargs)

        if not params["query"]:
            raise MissingArgumentError("query")

        # Set indices.
        indices = []
        if not params["indices"]:
            # By default, use the last two indices.
            today = libdatetime.utc_now()
            last_week = today - datetime.timedelta(days=7)

            index_template = self.context.get_index_template()
            indices = generate_list_of_indexes(last_week, today, index_template)
        elif len(params["indices"]) == 1 and params["indices"][0] == "ALL":
            # If we want all indices, just do nothing.
            pass
        else:
            indices = params["indices"]

        search_args = {}
        if indices:
            search_args["index"] = indices
            search_args["doc_type"] = self.context.get_doctype()

        connection = self.get_connection()

        try:
            results = connection.search(body=json.dumps(params["query"]), **search_args)
        except elasticsearch.exceptions.NotFoundError as e:
            missing_index = re.findall(BAD_INDEX_REGEX, e.error)[0]
            raise ResourceNotFound(
                "elasticsearch index '%s' does not exist" % missing_index
            )
        except elasticsearch.exceptions.TransportError as e:
            raise DatabaseError(e)

        return results

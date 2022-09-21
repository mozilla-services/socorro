# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
import datetime

from configman import class_converter, Namespace, RequiredConfig
import elasticsearch
from elasticsearch_dsl import Search

from socorro.external.es.super_search_fields import FIELDS


SUPERSEARCH_FIELDS = FIELDS


@dataclass
class IndexDataItem:
    name: str
    start_date: datetime.datetime
    count: int


class SuperSearchStatusModel(RequiredConfig):
    """Model that returns list of indices and latest mapping."""

    filters = []

    required_config = Namespace()
    required_config.add_option(
        "elasticsearch_class",
        doc="a class that implements the ES connection object",
        default="socorro.external.es.connection_context.ConnectionContext",
        from_string_converter=class_converter,
    )

    def __init__(self, config):
        self.config = config
        self.context = self.config.elasticsearch_class(self.config)

    def get_connection(self):
        with self.context() as conn:
            return conn

    def get(self):
        return self.get_supersearch_status()

    def get_supersearch_status(self):
        """Return list of indices, latest index, and mapping.

        :returns: list of IndexDataItem instances

        """
        conn = self.get_connection()
        index_client = elasticsearch.client.IndicesClient(conn)
        indices = sorted(self.context.get_indices())
        latest_index = indices[-1]

        doctype = self.context.get_doctype()
        index_template = self.context.get_index_template()
        if index_template.endswith("%Y%W"):
            # Doing strptime on a template that has %W but doesn't have a day-of-week,
            # will ignore the %W part; so we anchor it with 1 (Monday)
            add_day_of_week = True
            index_template = f"{index_template}%w"
        else:
            add_day_of_week = False

        index_data = []
        for index_name in indices:
            count = Search(using=conn, index=index_name, doc_type=doctype).count()

            if add_day_of_week:
                # %W starts on Mondays, so we set the day-of-week to 1 which is
                # Monday
                adjusted_index_name = f"{index_name}1"
            else:
                adjusted_index_name = index_name
            start_date = datetime.datetime.strptime(adjusted_index_name, index_template)
            start_date = start_date.date()

            index_data.append(
                IndexDataItem(
                    name=index_name,
                    start_date=start_date,
                    count=count,
                )
            )

        mapping = index_client.get_mapping(index=latest_index)
        mapping_properties = mapping[latest_index]["mappings"][doctype]["properties"]

        return {
            "indices": index_data,
            "latest_index": latest_index,
            "mapping": mapping_properties,
        }

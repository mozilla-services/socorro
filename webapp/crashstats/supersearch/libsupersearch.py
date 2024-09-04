# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
import datetime

import elasticsearch_1_9_0 as elasticsearch
from elasticsearch_dsl_0_0_11 import Search

from socorro import settings as socorro_settings
from socorro.external.legacy_es.super_search_fields import FIELDS
from socorro.libclass import build_instance_from_settings


# Map of processed crash schema permissions to webapp permissions
PROCESSED_CRASH_TO_WEBAPP_PERMISSIONS = {
    "public": "",
    "protected": "crashstats.view_pii",
}


def convert_permissions(fields):
    """Converts processed crash schema / super search permissions to webapp permissions

    :arg fields: super search fields structure to convert permissions of

    :returns: fields with permissions converted

    """

    def _convert(permissions):
        if not permissions:
            return permissions

        new_permissions = [
            PROCESSED_CRASH_TO_WEBAPP_PERMISSIONS[perm] for perm in permissions
        ]
        return [perm for perm in new_permissions if perm]

    for val in fields.values():
        val["permissions_needed"] = _convert(val["permissions_needed"])

    return fields


SUPERSEARCH_FIELDS = convert_permissions(FIELDS)


@dataclass
class IndexDataItem:
    name: str
    start_date: datetime.datetime
    count: int


class SuperSearchStatusModel:
    """Model that returns list of indices and latest mapping."""

    filters = []

    def __init__(self):
        self.es_crash_dest = build_instance_from_settings(socorro_settings.ES_STORAGE)

    def get_connection(self):
        with self.es_crash_dest.client() as conn:
            return conn

    def get(self):
        return self.get_supersearch_status()

    def get_supersearch_status(self):
        """Return list of indices, latest index, and mapping.

        :returns: list of IndexDataItem instances

        """
        conn = self.get_connection()
        index_client = elasticsearch.client.IndicesClient(conn)
        indices = sorted(self.es_crash_dest.get_indices())
        latest_index = indices[-1]

        doctype = self.es_crash_dest.get_doctype()
        index_template = self.es_crash_dest.get_index_template()
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

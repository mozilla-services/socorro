# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
import datetime

from socorro import settings as socorro_settings
from socorro.libclass import build_instance_from_settings


# Map of processed crash schema permissions to webapp permissions
PROCESSED_CRASH_TO_WEBAPP_PERMISSIONS = {
    "public": "",
    "protected": "crashstats.view_pii",
}


def convert_permissions(fields):
    """Converts processed crash schema / super search permissions to webapp permissions

    :arg fields: super search fields structure to convert permissions of

    :returns: fields with new "webapp_permissions_needed" value with webapp permissions

    """

    def _convert(permissions):
        if not permissions:
            return permissions

        new_permissions = [
            PROCESSED_CRASH_TO_WEBAPP_PERMISSIONS[perm] for perm in permissions
        ]
        return [perm for perm in new_permissions if perm]

    for val in fields.values():
        if "webapp_permissions_needed" not in val:
            val["webapp_permissions_needed"] = _convert(val["permissions_needed"])

    return fields


def get_supersearch_fields():
    es_crash_dest = build_instance_from_settings(socorro_settings.ES_STORAGE)
    return convert_permissions(es_crash_dest.SUPERSEARCH_FIELDS)


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
        indices = sorted(self.es_crash_dest.get_indices())
        latest_index = indices[-1]

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
            count = self.es_crash_dest.build_search(index=index_name).count()

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

        mapping_properties = self.es_crash_dest.get_mapping(latest_index)

        return {
            "indices": index_data,
            "latest_index": latest_index,
            "mapping": mapping_properties,
        }


def get_allowed_fields(user=None):
    """Return the names of SuperSearch fields the User may reference.

    :arg user: A Django User or ``None``. If ``None``, only fields with no
    permissions requirements are returned.

    :returns: tuple of field name strings.

    """

    def permissions_condition(field):
        if user is not None:
            return user.has_perms(field["webapp_permissions_needed"])
        return not field["webapp_permissions_needed"]

    fields = get_supersearch_fields().values()

    return tuple(
        x["name"] for x in fields if x["is_exposed"] and permissions_condition(x)
    )


def sanitize_list_of_fields_params(
    params, allowed_fields, list_of_fields_params=("_facets", "_columns", "_sort")
):
    """Strip disallowed field references from list-of-fields parameters.
    Handles _sort fields that may be prefixed with `-`.

    :arg params: dict of SuperSearch query parameters

    :arg list_of_fields_params: tuple of parameter names whose values are
    lists of field names

    :returns: the mutated ``params`` dict, with disallowed entries
    removed
    """
    allowed_fields_set = set(allowed_fields)

    for key in list_of_fields_params:
        # _sort: bare field name or with `-` prefix for reverse order.
        if key == "_sort":
            params[key] = [
                v
                for v in params.get(key, [])
                if v in allowed_fields_set
                or (v.startswith("-") and v[1:] in allowed_fields_set)
            ]
        # Other list-of-fields parameters (no `-` prefix)
        else:
            params[key] = [v for v in params.get(key, []) if v in allowed_fields_set]

    return params

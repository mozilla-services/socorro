import copy
import functools

from socorro.external.es import query
from socorro.external.es import supersearch
from socorro.external.es import super_search_fields

from django.core.cache import cache

from crashstats import scrubber
from crashstats.crashstats import models


SUPERSEARCH_META_PARAMS = (
    ('_aggs.product.version', list),
    ('_aggs.android_cpu_abi.android_manufacturer.android_model', list),
    ('_columns', list),
    ('_facets', list),
    ('_facets_size', int),
    '_fields',
    ('_results_offset', int),
    ('_results_number', int),
    '_return_query',
    ('_sort', list),
)


# Those parameters contain list of fields and thus need to be verified before
# sent to the middleware, so that no private field can be accessed.
PARAMETERS_LISTING_FIELDS = (
    '_aggs.product.version',
    '_aggs.android_cpu_abi.android_manufacturer.android_model',
    '_facets',
)


class SuperSearchFieldsWithoutConfig(super_search_fields.SuperSearchFields):
    """In the SuperSearchFields implementation class we know with confidence
    we can just call
    socorro.external.es.super_search_fields.SuperSearchFields.get() without
    first having instanciated the base class with the necessary configuration
    needed to reach Elasticsearch.

    This way we can call `.get()` on an instance of this class, which
    just returns the fields.
    """

    def __init__(self, *args, **kwargs):
        # Deliberately don't do anything
        pass


def get_api_whitelist(include_all_fields=False):

    def get_from_es(include_all_fields):
        cache_key = 'api_supersearch_fields'
        fields = cache.get(cache_key)
        if fields is None:
            all = SuperSearchFields().get()
            fields = []
            for meta in all.itervalues():
                if (
                    meta['name'] not in fields and
                    meta['is_returned'] and (
                        include_all_fields or
                        not meta['permissions_needed']
                    )
                ):
                    fields.append(meta['name'])
            fields = tuple(fields)

            # Cache for 1 hour.
            cache.set(cache_key, fields, 60 * 60)
        return {'hits': fields}

    return functools.partial(get_from_es, include_all_fields)


class ESSocorroMiddleware(models.SocorroMiddleware):

    implementation_config_namespace = 'elasticsearch'


class SuperSearch(ESSocorroMiddleware):

    implementation = supersearch.SuperSearch

    API_WHITELIST = get_api_whitelist()

    API_CLEAN_SCRUB = (
        ('user_comments', scrubber.EMAIL),
        ('user_comments', scrubber.URL),
    )

    def __init__(self):
        self.all_fields = SuperSearchFields().get()

        # These fields contain lists of other fields. Later on, we want to
        # make sure that none of those listed fields are restricted.
        self.parameters_listing_fields = list(PARAMETERS_LISTING_FIELDS)

        self.required_params = tuple(
            (x['name'], list) for x in self.all_fields.values()
            if x['is_exposed'] and
            not x['permissions_needed'] and
            x['is_mandatory']
        )

        self.extended_fields = self._get_extended_params()
        for field in self.extended_fields:
            if '_histogram.' in field[0] or '_aggs.' in field[0]:
                self.parameters_listing_fields.append(field[0])

        self.possible_params = tuple(
            (x['name'], list) for x in self.all_fields.values()
            if x['is_exposed'] and
            not x['permissions_needed'] and
            not x['is_mandatory']
        ) + SUPERSEARCH_META_PARAMS + tuple(self.extended_fields)

    def _get_extended_params(self):
        # Add histogram fields for all 'date' or 'number' fields.
        extended_fields = []
        for field in self.all_fields.values():
            if not field['is_exposed'] or field['permissions_needed']:
                continue

            extended_fields.append(
                ('_aggs.%s' % field['name'], list)
            )

            if field['query_type'] in ('date', 'number'):
                extended_fields.append(
                    ('_histogram.%s' % field['name'], list)
                )

                # Intervals can be strings for dates (like "day" or "1.5h")
                # and can only be integers for numbers.
                interval_type = {
                    'date': basestring,
                    'number': int
                }.get(field['query_type'])

                extended_fields.append(
                    ('_histogram_interval.%s' % field['name'], interval_type)
                )

        return tuple(extended_fields)

    def get(self, **kwargs):
        # Sanitize all parameters listing fields and make sure no private data
        # is requested.

        # Initialize the list of allowed fields with all the fields we know
        # that are returned and do not require any permission.
        allowed_fields = set(
            x for x in self.all_fields
            if self.all_fields[x]['is_returned'] and
            not self.all_fields[x]['permissions_needed']
        )

        # Extend that list with the special fields, like `_histogram.*`.
        # Those are accepted values for fields listing other fields.
        for field in self.extended_fields:
            histogram = field[0]
            if not histogram.startswith('_histogram.'):
                continue

            field_name = histogram[len('_histogram.'):]
            if (
                field_name in self.all_fields and
                self.all_fields[field_name]['is_returned'] and
                not self.all_fields[field_name]['permissions_needed']
            ):
                allowed_fields.add(histogram)

        for field in set(allowed_fields):
            allowed_fields.add('_cardinality.%s' % field)

        # Now make sure all fields listing fields only have unrestricted
        # values.
        for param in self.parameters_listing_fields:
            values = kwargs.get(param, [])
            filtered_values = [
                x for x in values
                if x in allowed_fields
            ]
            kwargs[param] = filtered_values

        # SuperSearch requires that the list of fields be passed to it.
        kwargs['_fields'] = self.all_fields

        return super(SuperSearch, self).get(**kwargs)


class SuperSearchUnredacted(SuperSearch):

    API_WHITELIST = get_api_whitelist(include_all_fields=True)

    API_CLEAN_SCRUB = None

    def __init__(self):
        self.all_fields = SuperSearchFields().get()

        self.required_params = tuple(
            (x['name'], list) for x in self.all_fields.values()
            if x['is_exposed'] and x['is_mandatory']
        )

        histogram_fields = self._get_extended_params()

        self.possible_params = tuple(
            (x['name'], list) for x in self.all_fields.values()
            if x['is_exposed'] and not x['is_mandatory']
        ) + SUPERSEARCH_META_PARAMS + histogram_fields

        permissions = {}
        for field_data in self.all_fields.values():
            for perm in field_data['permissions_needed']:
                permissions[perm] = True

        self.API_REQUIRED_PERMISSIONS = tuple(permissions.keys())

    def get(self, **kwargs):
        # SuperSearch requires that the list of fields be passed to it.
        kwargs['_fields'] = self.all_fields

        # Notice that here we use `SuperSearch` as the class, so that we
        # shortcut the `get` function in that class. The goal is to avoid
        # the _facets field cleaning.
        return super(SuperSearch, self).get(**kwargs)


class SuperSearchFields(ESSocorroMiddleware):

    # Read it in once as a class attribute since it'll never change unless the
    # Python code changes and if that happens you will have reloaded the
    # Python process.
    _fields = SuperSearchFieldsWithoutConfig().get()

    API_WHITELIST = None

    def get(self):
        return copy.deepcopy(self._fields)


class SuperSearchMissingFields(ESSocorroMiddleware):

    implementation = super_search_fields.SuperSearchMissingFields

    # This service's data doesn't change a lot over time, it's fine to cache
    # it for a long time.
    cache_seconds = 60 * 60 * 12  # 12 hours


class Query(ESSocorroMiddleware):
    # No API_WHITELIST because this can't be accessed through the public API.

    implementation = query.Query

    required_params = (
        'query',
    )

    possible_params = (
        'indices',
    )

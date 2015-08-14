import functools
import json

from socorro.external.es import supersearch
from socorro.external.es import super_search_fields

from django.core.cache import cache

from crashstats import scrubber
from crashstats.crashstats import models


SUPERSEARCH_META_PARAMS = (
    ('_aggs.signature', list),
    ('_columns', list),
    ('_facets', list),
    ('_facets_size', int),
    ('_results_offset', int),
    ('_results_number', int),
    '_return_query',
    ('_sort', list),
)


# Those parameters contain list of fields and thus need to be verified before
# sent to the middleware, so that no private field can be accessed.
PARAMETERS_LISTING_FIELDS = (
    '_facets',
    '_aggs.signature',
)


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
        return fields

    return models.Lazy(
        functools.partial(get_from_es, include_all_fields)
    )


class SuperSearch(models.SocorroMiddleware):

    implementation = supersearch.SuperSearch

    API_WHITELIST = {
        'hits': get_api_whitelist()
    }

    API_CLEAN_SCRUB = (
        ('user_comments', scrubber.EMAIL),
        ('user_comments', scrubber.URL),
    )

    def __init__(self):
        all_fields = SuperSearchFields().get()

        self.parameters_listing_fields = list(PARAMETERS_LISTING_FIELDS)

        self.required_params = tuple(
            (x['name'], list) for x in all_fields.values()
            if x['is_exposed']
            and not x['permissions_needed']
            and x['is_mandatory']
        )

        histogram_fields = self._get_extended_params(all_fields)
        for field in histogram_fields:
            if '_histogram.' in field[0]:
                self.parameters_listing_fields.append(field[0])

        self.possible_params = tuple(
            (x['name'], list) for x in all_fields.values()
            if x['is_exposed']
            and not x['permissions_needed']
            and not x['is_mandatory']
        ) + SUPERSEARCH_META_PARAMS + tuple(histogram_fields)

    def _get_extended_params(self, all_fields):
        # Add histogram fields for all 'date' or 'number' fields.
        histogram_fields = []
        for field in all_fields.values():
            if (
                field['is_exposed']
                and not field['permissions_needed']
                and field['query_type'] in ('date', 'number')
            ):
                histogram_fields.append(
                    ('_histogram.%s' % field['name'], list)
                )

                # Intervals can be strings for dates (like "day" or "1.5h")
                # and can only be integers for numbers.
                interval_type = {
                    'date': basestring,
                    'number': int
                }.get(field['query_type'])

                histogram_fields.append(
                    ('_histogram_interval.%s' % field['name'], interval_type)
                )

        return tuple(histogram_fields)

    def get(self, **kwargs):
        # Sanitize all parameters listing fields and make sure no private data
        # is requested.
        all_fields = SuperSearchFields().get()
        for param in self.parameters_listing_fields:
            values = kwargs.get(param)
            filtered_values = [
                x for x in values
                if x in all_fields
                and all_fields[x]['is_returned']
                and not all_fields[x]['permissions_needed']
            ]
            kwargs[param] = filtered_values

        return super(SuperSearch, self).get(**kwargs)


class SuperSearchUnredacted(SuperSearch):

    API_WHITELIST = {
        'hits': get_api_whitelist(include_all_fields=True)
    }

    API_CLEAN_SCRUB = None

    def __init__(self):
        all_fields = SuperSearchFields().get()

        self.required_params = tuple(
            (x['name'], list) for x in all_fields.values()
            if x['is_exposed'] and x['is_mandatory']
        )

        histogram_fields = self._get_extended_params(all_fields)

        self.possible_params = tuple(
            (x['name'], list) for x in all_fields.values()
            if x['is_exposed'] and not x['is_mandatory']
        ) + SUPERSEARCH_META_PARAMS + histogram_fields

        permissions = {}
        for field_data in all_fields.values():
            for perm in field_data['permissions_needed']:
                permissions[perm] = True

        self.API_REQUIRED_PERMISSIONS = tuple(permissions.keys())

    def get(self, **kwargs):
        # Notice that here we use `SuperSearch` as the class, so that we
        # shortcut the `get` function in that class. The goal is to avoid
        # the _facets field cleaning.
        return super(SuperSearch, self).get(**kwargs)


class SuperSearchFields(models.SocorroMiddleware):

    implementation = super_search_fields.SuperSearchFields

    # The only reason this data will change is if a user changes it via the UI.
    # If that happens, the cache will be reset automatically. We can thus
    # increase the cache a lot here.
    cache_seconds = 60 * 60 * 24  # 24 hours


class SuperSearchMissingFields(models.SocorroMiddleware):

    implementation = super_search_fields.SuperSearchMissingFields

    # This service's data doesn't change a lot over time, it's fine to cache
    # it for a long time.
    cache_seconds = 60 * 60 * 12  # 12 hours


class SuperSearchField(models.SocorroMiddleware):

    implementation = super_search_fields.SuperSearchFields

    required_params = (
        'name',
    )

    possible_params = (
        'namespace',
        'in_database_name',
        'description',
        'query_type',
        'data_validation_type',
        'permissions_needed',
        'form_field_choices',
        'is_exposed',
        'is_returned',
        'is_mandatory',
        'has_full_version',
        'storage_mapping',
    )

    def get(self, **kwargs):
        raise NotImplemented()

    def create_field(self, **kwargs):
        # print "IMPL", self.get_implementation()
        return self.get_implementation().create_field(**kwargs)

    def update_field(self, **kwargs):
        return self.get_implementation().update_field(**kwargs)

    def delete_field(self, **kwargs):
        return self.get_implementation().delete_field(**kwargs)

    def post(self, payload):
        raise NotImplementedError('Use create_field')

    def put(self, payload):
        raise NotImplementedError('Use update_field')


class Query(models.SocorroMiddleware):
    # No API_WHITELIST because this can't be accessed through the public API.

    URL_PREFIX = '/query/'

    required_params = (
        'query',
    )

    possible_params = (
        'indices',
    )

    def get(self, **kwargs):
        params = self.kwargs_to_params(kwargs)
        payload = {
            'query': json.dumps(params['query']),
            'indices': params.get('indices'),
        }
        return self.post(self.URL_PREFIX, payload)

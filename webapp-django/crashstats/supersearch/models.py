import functools
import json

from django.core.cache import cache

from crashstats import scrubber
from crashstats.crashstats import models


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

    URL_PREFIX = '/supersearch/'

    API_WHITELIST = {
        'hits': get_api_whitelist()
    }

    API_CLEAN_SCRUB = (
        ('user_comments', scrubber.EMAIL),
        ('user_comments', scrubber.URL),
    )

    def __init__(self):
        all_fields = SuperSearchFields().get()

        self.required_params = tuple(
            (x['name'], list) for x in all_fields.values()
            if x['is_exposed']
            and not x['permissions_needed']
            and x['is_mandatory']
        )

        self.possible_params = tuple(
            (x['name'], list) for x in all_fields.values()
            if x['is_exposed']
            and not x['permissions_needed']
            and not x['is_mandatory']
        ) + (
            ('_facets', list),
            ('_results_offset', int),
            ('_results_number', int),
            '_return_query',
        )


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

        self.possible_params = tuple(
            (x['name'], list) for x in all_fields.values()
            if x['is_exposed'] and not x['is_mandatory']
        ) + (
            ('_facets', list),
            ('_results_offset', int),
            ('_results_number', int),
            '_return_query',
        )

        permissions = {}
        for field_data in all_fields.values():
            for perm in field_data['permissions_needed']:
                permissions[perm] = True

        self.API_REQUIRED_PERMISSIONS = tuple(permissions.keys())


class SuperSearchFields(models.SocorroMiddleware):

    URL_PREFIX = '/supersearch/fields/'

    # The only reason this data will change is if a user changes it via the UI.
    # If that happens, the cache will be reset automatically. We can thus
    # increase the cache a lot here.
    cache_seconds = 60 * 60 * 24


class SuperSearchMissingFields(models.SocorroMiddleware):

    URL_PREFIX = '/supersearch/missing_fields/'

    # This service's data doesn't change a lot over time, it's fine to cache
    # it for a long time.
    cache_seconds = 60 * 60 * 12  # 12 hours


class SuperSearchField(models.SocorroMiddleware):

    URL_PREFIX = '/supersearch/field/'

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

    def post(self, payload):
        return super(SuperSearchField, self).post(self.URL_PREFIX, payload)

    def put(self, payload):
        return super(SuperSearchField, self).put(self.URL_PREFIX, payload)


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

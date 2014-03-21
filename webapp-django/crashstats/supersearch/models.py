import json

from crashstats.crashstats import models

from . import forms


class SuperSearch(models.SocorroMiddleware):

    URL_PREFIX = '/supersearch/'

    # Generate the list of possible parameters from the associated form.
    # This way we only manage one list of parameters.
    possible_params = tuple(
        x for x in forms.SearchForm([], [], [], True, True).fields
    ) + (
        '_facets',
        '_results_offset',
        '_results_number',
        '_return_query',
    )


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

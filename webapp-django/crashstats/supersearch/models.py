from crashstats.crashstats import models

import forms


class SuperSearch(models.SocorroMiddleware):

    URL_PREFIX = '/supersearch/'

    # Generate the list of possible parameters from the associated form.
    # This way we only manage one list of parameters.
    possible_params = tuple(
        x for x in forms.SearchForm([], [], []).fields
    ) + (
        '_results_offset',
        '_results_number',
        '_facets',
    )

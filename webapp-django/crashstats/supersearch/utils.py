import datetime

import isodate

from django.utils import timezone

from crashstats.supersearch.form_fields import split_on_operator


DEFAULT_RANGE_DAYS = 7


def get_date_boundaries(params):
    """Return the date boundaries in a set of parameters.

    Return a tuple with 2 datetime objects, the first one is the lower bound
    date and the second one is the upper bound date.
    """
    default_date_range = datetime.timedelta(days=DEFAULT_RANGE_DAYS)

    start_date = None
    end_date = None

    if not params.get('date'):
        end_date = timezone.now()
        start_date = end_date - default_date_range
    else:
        for param in params['date']:
            d = isodate.parse_datetime(
                split_on_operator(param)[1]
            ).replace(tzinfo=timezone.utc)

            if param.startswith('<') and (not end_date or end_date < d):
                end_date = d
            if param.startswith('>') and (not start_date or start_date > d):
                start_date = d

        if not end_date:
            end_date = timezone.now()

        if not start_date:
            start_date = end_date - default_date_range

    return (start_date, end_date)

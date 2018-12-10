from six.moves.urllib.parse import urlencode

from django.template import engines
from django.utils.functional import cached_property


def render_exception(exception):
    """When we need to render an exception as HTML.

    Often used to supply as the response body when there's a
    HttpResponseBadRequest.
    """
    template = engines['backend'].from_string(
        '<ul><li>{{ exception }}</li></ul>'
    )
    return template.render({'exception': exception})


def urlencode_obj(thing):
    """Return a URL encoded string, created from a regular dict or any object
    that has a `urlencode` method.

    This function ensures white spaces are encoded with '%20' and not '+'.
    """
    if hasattr(thing, 'urlencode'):
        res = thing.urlencode()
    else:
        res = urlencode(thing, True)
    return res.replace('+', '%20')


class SignatureStats(object):
    def __init__(
        self,
        signature,
        num_total_crashes,
        rank=0,
        platforms=None,
        previous_signature=None
    ):
        self.signature = signature
        self.num_total_crashes = num_total_crashes
        self.rank = rank
        self.platforms = platforms
        self.previous_signature = previous_signature

    @cached_property
    def platform_codes(self):
        return [x['short_name'] for x in self.platforms if x['short_name'] != 'unknown']

    @cached_property
    def signature_term(self):
        return self.signature['term']

    @cached_property
    def percent_of_total_crashes(self):
        return 100.0 * self.signature['count'] / self.num_total_crashes

    @cached_property
    def num_crashes(self):
        return self.signature['count']

    @cached_property
    def num_crashes_per_platform(self):
        num_crashes_per_platform = {platform + '_count': 0 for platform in self.platform_codes}
        for platform in self.signature['facets']['platform']:
            code = platform['term'][:3].lower()
            if code in self.platform_codes:
                num_crashes_per_platform[code + '_count'] = platform['count']
        return num_crashes_per_platform

    @cached_property
    def num_crashes_in_garbage_collection(self):
        num_crashes_in_garbage_collection = 0
        for row in self.signature['facets']['is_garbage_collecting']:
            if row['term'].lower() == 't':
                num_crashes_in_garbage_collection = row['count']
        return num_crashes_in_garbage_collection

    @cached_property
    def num_installs(self):
        return self.signature['facets']['cardinality_install_time']['value']

    @cached_property
    def percent_of_total_crashes_diff(self):
        if self.previous_signature:
            return self.previous_signature.percent_of_total_crashes - self.percent_of_total_crashes
        return 'new'

    @cached_property
    def rank_diff(self):
        if self.previous_signature:
            return self.previous_signature.rank - self.rank
        return 0

    @cached_property
    def previous_percent_of_total_crashes(self):
        if self.previous_signature:
            return self.previous_signature.percent_of_total_crashes
        return 0

    @cached_property
    def num_startup_crashes(self):
        return sum(
            row['count'] for row in self.signature['facets']['startup_crash']
            if row['term'] in ('T', '1')
        )

    @cached_property
    def is_startup_crash(self):
        return self.num_startup_crashes == self.num_crashes

    @cached_property
    def is_potential_startup_crash(self):
        return self.num_startup_crashes > 0 and self.num_startup_crashes < self.num_crashes

    @cached_property
    def is_startup_window_crash(self):
        is_startup_window_crash = False
        for row in self.signature['facets']['histogram_uptime']:
            # Aggregation buckets use the lowest value of the bucket as
            # term. So for everything between 0 and 60 excluded, the
            # term will be `0`.
            if row['term'] < 60:
                ratio = 1.0 * row['count'] / self.num_crashes
                is_startup_window_crash = ratio > 0.5
        return is_startup_window_crash

    @cached_property
    def is_hang_crash(self):
        num_hang_crashes = 0
        for row in self.signature['facets']['hang_type']:
            # Hangs have weird values in the database: a value of 1 or -1
            # means it is a hang, a value of 0 or missing means it is not.
            if row['term'] in (1, -1):
                num_hang_crashes += row['count']
        return num_hang_crashes > 0

    @cached_property
    def is_plugin_crash(self):
        for row in self.signature['facets']['process_type']:
            if row['term'].lower() == 'plugin':
                return row['count'] > 0
        return False

    @cached_property
    def is_startup_related_crash(self):
        return self.is_startup_crash \
            or self.is_potential_startup_crash \
            or self.is_startup_window_crash


def get_comparison_signatures(results):
    comparison_signatures = {}
    for index, signature in enumerate(results['facets']['signature']):
        signature_stats = SignatureStats(
            signature=signature,
            rank=index,
            num_total_crashes=results['total'],
            platforms=None,
            previous_signature=None,
        )
        comparison_signatures[signature_stats.signature_term] = signature_stats
    return comparison_signatures

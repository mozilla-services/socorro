from crashstats.base.tests.testbase import TestCase
from crashstats.base.utils import render_exception, SignatureStats


class TestRenderException(TestCase):

    def test_basic(self):
        html = render_exception('hi!')
        assert html == '<ul><li>hi!</li></ul>'

    def test_escaped(self):
        html = render_exception('<hi>')
        assert html == '<ul><li>&lt;hi&gt;</li></ul>'

    def test_to_string(self):
        try:
            raise NameError('<hack>')
        except NameError as exc:
            html = render_exception(exc)
        assert html == '<ul><li>&lt;hack&gt;</li></ul>'


class TestUtils(TestCase):
    def test_SignatureStats(self):
        signature = {
            'count': 2,
            'term': 'EMPTY: no crashing thread identified; ERROR_NO_MINIDUMP_HEADER',
            'facets': {
                'histogram_uptime': [{
                    'count': 2,
                    'term': 0
                }],
                'startup_crash': [{
                    'count': 2,
                    'term': 'F'
                }],
                'cardinality_install_time': {
                    'value': 1
                },
                'is_garbage_collecting': [],
                'process_type': [],
                'platform': [{
                    'count': 2,
                    'term': ''
                }],
                'hang_type': [{
                    'count': 2,
                    'term': 0
                }]
            }
        }
        platforms = [
            {'code': 'win', 'name': 'Windows'},
            {'code': 'mac', 'name': 'Mac OS X'},
            {'code': 'lin', 'name': 'Linux'},
            {'code': 'unknown', 'name': 'Unknown'}]
        signature_stats = SignatureStats(
            signature=signature,
            rank=1,
            num_total_crashes=2,
            platforms=platforms,
            previous_signature=None,
        )

        assert signature_stats.rank == 1
        assert signature_stats.signature_term \
            == 'EMPTY: no crashing thread identified; ERROR_NO_MINIDUMP_HEADER'
        assert signature_stats.percent_of_total_crashes == 100.0
        assert signature_stats.num_crashes == 2
        assert signature_stats.num_crashes_per_platform \
            == {'mac_count': 0, 'lin_count': 0, 'win_count': 0}
        assert signature_stats.num_crashes_in_garbage_collection == 0
        assert signature_stats.num_installs == 1
        assert signature_stats.num_crashes == 2
        assert signature_stats.num_startup_crashes == 0
        assert signature_stats.is_startup_crash == 0
        assert signature_stats.is_potential_startup_crash == 0
        assert signature_stats.is_startup_window_crash is True
        assert signature_stats.is_hang_crash is False
        assert signature_stats.is_plugin_crash is False

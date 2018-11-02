from crashstats.api.templatetags.jinja_helpers import pluralize


class TestPluralize(object):
    def test_basics(self):
        assert pluralize(0) == 's'
        assert pluralize(1) == ''
        assert pluralize(59) == 's'

    def test_overide_s(self):
        assert pluralize(59, 'ies') == 'ies'

import json
from past.builtins import basestring

from crashstats.crashstats.tests.test_models import Response


class SuperSearchResponse(Response):
    def __init__(self, content=None, status_code=200, columns=None):
        if isinstance(content, basestring):
            content = json.loads(content)

        if columns is None:
            columns = []

        assert 'hits' in content
        for i, hit in enumerate(content['hits']):
            content['hits'][i] = dict(
                (key, val)
                for key, val in hit.items()
                if key in columns
            )

        super(SuperSearchResponse, self).__init__(content, status_code)

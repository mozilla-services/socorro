import unittest

from socorro.external.elasticsearch.search import Search

import socorro.lib.util as util
import socorro.unittest.testlib.util as tutil


def setup_module():
    tutil.nosePrintModule(__file__)


def get_dummy_context():
    """
    Create a dummy config object to use when testing.
    """
    context = util.DotDict()
    context.elasticSearchHostname = ""
    context.elasticSearchPort = 9200
    context.platforms = (
        {
            "id": "windows",
            "name": "Windows NT"
        },
        {
            "id": "linux",
            "name": "Linux"
        }
    )
    return context


def test_get_signatures():
    """
    Test Search.get_signatures()
    """
    context = get_dummy_context()
    facets = {
        "signatures": {
            "terms": [
                {
                    "term": "hang",
                    "count": 145
                },
                {
                    "term": "js",
                    "count": 7
                },
                {
                    "term": "ws",
                    "count": 4
                }
            ]
        }
    }
    size = 3
    expected = ["hang", "js", "ws"]
    signatures = Search.get_signatures(facets, size, context.platforms)
    res_signs = []
    for sign in signatures:
        assert sign["signature"] in expected, (
                    "get_signatures returned an unexpected signature: %s" %
                    sign["signature"])
        res_signs.append(sign["signature"])

    for sign in expected:
        assert sign in res_signs, (
                    "An expected signature is missing: %s" % sign)


def test_get_counts():
    """
    Test Search.get_counts()
    """
    context = get_dummy_context()
    signatures = [
        {
            "signature": "hang",
            "count": 12
        },
        {
            "signature": "js",
            "count": 4
        }
    ]
    count_sign = {
        "hang": {
            "terms": [
                {
                    "term": "windows",
                    "count": 3
                },
                {
                    "term": "linux",
                    "count": 4
                }
            ]
        },
        "js": {
            "terms": [
                {
                    "term": "windows",
                    "count": 2
                }
            ]
        },
        "hang_hang": {
            "count": 0
        },
        "js_hang": {
            "count": 0
        },
        "hang_plugin": {
            "count": 0
        },
        "js_plugin": {
            "count": 0
        },
        "hang_content": {
            "count": 0
        },
        "js_content": {
            "count": 0
        }
    }
    res = Search.get_counts(signatures, count_sign, 0, 2, context.platforms)

    assert type(res) is list, "Not a list"
    for sign in res:
        assert "signature" in sign, "no signature"
        assert "count" in sign, "no count"
        assert "is_windows" in sign, "no windows"
        assert "numhang" in sign, "no hang"
        assert "numplugin" in sign, "no plugin"
        assert "numcontent" in sign, "no content"

    assert "is_linux" in res[0], "no linux"
    assert "is_linux" not in res[1], "need no linux"

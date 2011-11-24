import unittest

from socorro.external.elasticsearch.base import ElasticSearchBase

import socorro.lib.search_common as scommon
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


def test_build_query_from_params():
    """
    Test ElasticSearchBase.build_query_from_params()
    """
    # Test with all default parameters
    args = {
        "config": get_dummy_context()
    }
    search = ElasticSearchBase(**args)
    params = {}
    params = scommon.get_parameters(params)
    query = ElasticSearchBase.build_query_from_params(params)
    assert query, "build_query_from_params returned a bad value: %s" % query
    assert "query" in query, (
                "query is malformed, 'query' key missing: %s" % query)
    assert "size" in query, (
                "query is malformed, 'size' key missing: %s" % query)
    assert "from" in query, (
                "query is malformed, 'from' key missing: %s" % query)

    # Searching for a term in a specific field and with a specific product
    params = {
        "terms": "hang",
        "fields": "dump",
        "search_mode": "contains",
        "products": "fennec"
    }
    params = scommon.get_parameters(params)
    query = ElasticSearchBase.build_query_from_params(params)
    assert query, "build_query_from_params returned a bad value: %s" % query
    assert "query" in query, (
                "query is malformed, 'query' key missing: %s" % query)
    assert "filtered" in query["query"], (
                "query is malformed, 'filtered' key missing: %s" % query)

    filtered = query["query"]["filtered"]
    assert "query" in filtered, (
                "query is malformed,  'query' key missing: %s" % query)
    assert "wildcard" in filtered["query"], (
                "query is malformed, 'wildcard' key missing: %s" % query)
    assert "dump" in filtered["query"]["wildcard"], (
                "query is malformed, 'dump' key missing: %s" % query)

    dump_term = filtered["query"]["wildcard"]["dump"]
    assert "*hang*" == dump_term, (
                "query is malformed, value for wildcard is wrong: %s" % query)
    assert "filter" in filtered, (
                "query is malformed, 'filter' key missing: %s" % query)
    assert "and" in filtered["filter"], (
                "query is malformed, 'and' key missing: %s" % query)


def test_build_terms_query():
    """
    Test ElasticSearchBase.build_terms_query()
    """
    # Empty query
    fields = ""
    terms = None
    query = ElasticSearchBase.build_terms_query(fields, terms)
    assert not query

    # Single term, single field query
    fields = "signature"
    terms = "hang"
    query = ElasticSearchBase.build_terms_query(fields, terms)
    assert "term" in query, (
                "Single term, single field query does not have a term field: "
                "%s" % query)
    assert fields in query["term"], (
                "Term query does not have the asked %s field: %s" %
                (fields, query))
    assert query["term"][fields] == terms, (
                "Term query's value is %s, should be %s in query %s" %
                (query["term"][fields], terms, query))

    # Multiple terms, single field query
    fields = "signature"
    terms = ["hang", "flash", "test"]
    query = ElasticSearchBase.build_terms_query(fields, terms)
    assert "terms" in query, (
                "Single term, single field query does not have a term field: "
                "%s" % query)
    assert fields in query["terms"], (
                "Term query does not have the asked %s field: %s" %
                (fields, query))
    assert query["terms"][fields] == terms, (
                "Term query's value is %s, should be %s in query %s" %
                (query["term"][fields], terms, query))

    # Multiple terms, multiple fields query
    fields = ["signature", "dump"]
    terms = ["hang", "flash"]
    query = ElasticSearchBase.build_terms_query(fields, terms)
    assert "terms" in query, (
                "Single term, single field query does not have a term field: "
                "%s" % query)
    for field in fields:
        assert field in query["terms"], (
                    "Term query does not have the asked %s field: %s" %
                    (field, query))
        assert query["terms"][field] == terms, (
                    "Term query's value is %s, should be %s in query %s" %
                    (query["term"][field], terms, query))


def test_build_wildcard_query():
    """
    Test ElasticSearchBase.build_wildcard_query()
    """
    # Empty query
    fields = ""
    terms = None
    query = ElasticSearchBase.build_wildcard_query(fields, terms)
    assert not query, "Query is %s, null or empty expected." % query

    # Single term, single field query
    fields = "signature"
    terms = "hang"
    query = ElasticSearchBase.build_wildcard_query(fields, terms)
    assert "wildcard" in query, (
                "Single term, single field query does not have "
                "a wildcard field: %s" % query)
    assert "signature.full" in query["wildcard"], (
                "Term query does not have the asked %s field: %s" %
                (fields, query))
    assert query["wildcard"]["signature.full"] == terms, (
                "Term query's value is %s, should be %s in query %s" %
                (query["term"][fields], terms, query))

    # Multiple terms, single field query
    fields = "dump"
    terms = ["hang", "flash", "test"]
    query = ElasticSearchBase.build_wildcard_query(fields, terms)
    assert "wildcard" in query, (
                "Single term, single field query does not have "
                "a wildcard field: %s" % query)
    assert fields in query["wildcard"], (
                "Term query does not have the asked %s field: %s" %
                (fields, query))
    assert query["wildcard"][fields] == terms, (
                "Term query's value is %s, should be %s in query %s" %
                (query["term"][fields], terms, query))

    # Multiple terms, multiple fields query
    fields = ["reason", "dump"]
    terms = ["hang", "flash"]
    query = ElasticSearchBase.build_wildcard_query(fields, terms)
    assert "wildcard" in query, (
                "Single term, single field query does not have "
                "a wildcard field: %s" % query)
    for field in fields:
        assert field in query["wildcard"], (
                    "Term query does not have the asked %s field: %s" %
                    (field, query))
        assert query["wildcard"][field] == terms, (
                    "Term query's value is %s, should be %s in query %s" %
                    (query["term"][field], terms, query))


def test_format_versions():
    """
    Test ElasticSearchBase.format_versions()
    """
    # Empty versions
    versions = None
    version_res = ElasticSearchBase.format_versions(versions)
    assert not version_res, (
                "The versions string is %s, null expected." % version_res)

    # Only one product, no version
    versions = ["firefox"]
    version_res = ElasticSearchBase.format_versions(versions)
    assert isinstance(version_res, list), (
                "Results should be a list, %s received" % type(version_res))
    assert version_res == [{ "product": "firefox", "version": None}], (
                "Wrong formatting of versions for one product, no version: "
                "%s" % version_res)

    # One product, one version
    versions = ["firefox:5.0.1b"]
    version_res = ElasticSearchBase.format_versions(versions)
    assert isinstance(version_res, list), (
                "Results should be a list, %s received" % type(version_res))
    assert "product" in version_res[0], "Result should have a product"
    assert "version" in version_res[0], "Result should have a version"
    assert version_res[0]["product"] == "firefox", (
                "Result's product is wrong, expected 'firefox', received %s" %
                version_res[0]["product"])
    assert version_res[0]["version"] == "5.0.1b", (
                "Result's version is wrong, expected '5.0.1b', received %s" %
                version_res[0]["version"])

    # Multiple products, multiple versions
    versions = ["firefox:5.0.1b", "fennec:1"]
    version_res = ElasticSearchBase.format_versions(versions)
    assert type(version_res) is list, (
                "Results should be a list, %s received" % type(version_res))
    for v in version_res:
        assert "product" in v, "Result should have a product"
        assert "version" in v, "Result should have a version"

    assert version_res[0]["product"] == "firefox", (
                "Result's product is wrong, expected 'firefox', received %s" %
                version_res[0]["product"])
    assert version_res[0]["version"] == "5.0.1b", (
                "Result's version is wrong, expected '5.0.1b', received %s" %
                version_res[0]["version"])
    assert version_res[1]["product"] == "fennec", (
                "Result's product is wrong, expected 'fennec', received %s" %
                version_res[1]["product"])
    assert version_res[1]["version"] == "1", (
                "Result's version is wrong, expected '1', received %s" %
                version_res[1]["version"])

def test_prepare_terms():
    """
    Test Search.prepare_terms()
    """
    # Empty terms
    terms = []
    search_mode = None
    newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
    assert not newterms, "Terms are %s, null or empty expected." % newterms

    # Contains mode, single term
    terms = ["test"]
    search_mode = "contains"
    newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
    assert newterms == "*test*", (
                "Terms are not well prepared, missing stars around: %s" %
                newterms)

    # Contains mode, multiple terms
    terms = ["test", "hang"]
    search_mode = "contains"
    newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
    assert newterms == "*test hang*", (
                "Terms are not well prepared, missing stars around: %s" %
                newterms)

    # Starts with mode, multiple terms
    terms = ["test", "hang"]
    search_mode = "starts_with"
    newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
    assert newterms == "test hang*", (
                "Terms are not well prepared, missing stars after: %s" %
                newterms)

    # Is exactly mode, multiple terms
    terms = ["test", "hang"]
    search_mode = "is_exactly"
    newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
    assert newterms == " ".join(terms), (
                "Terms should be concatenated when using a is_exactly mode.")

    # Random unexisting mode, multiple terms
    terms = ["test", "hang"]
    search_mode = "random_unexisting_mode"
    newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
    assert newterms == terms, (
                "Terms should not be changed when using a mode other than "
                "is_exactly, starts_with or contains.")

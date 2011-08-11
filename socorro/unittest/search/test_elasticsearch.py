import socorro.search.searchapi as sapi
import socorro.search.elasticsearch as es
import socorro.lib.util as util


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
    Test ElasticSearchAPI.get_signatures()

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
    signatures = es.ElasticSearchAPI.get_signatures(facets, size,
                                                    context.platforms)
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
    Test ElasticSearchAPI.get_counts()

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
        }
    }
    res = es.ElasticSearchAPI.get_counts(signatures, count_sign, 0, 2,
                                         context.platforms)

    assert type(res) is list, "Not a list"
    for sign in res:
        assert "signature" in sign, "no signature"
        assert "count" in sign, "no count"
        assert "is_windows" in sign, "no windows"
        assert "numhang" in sign, "no hang"
        assert "numplugin" in sign, "no plugin"

    assert "is_linux" in res[0], "no linux"
    assert "is_linux" not in res[1], "need no linux"


def test_build_query_from_params():
    """
    Test ElasticSearchAPI.build_query_from_params()

    """
    # Test with all default parameters
    params = {}
    params = sapi.SearchAPI.get_parameters(params)
    query = es.ElasticSearchAPI.build_query_from_params(params)
    assert query, "build_query_from_params returned a bad value: %s" % query
    assert "query" in query, (
                "query is malformed, 'query' key missing: %s" % query)
    assert "size" in query, (
                "query is malformed, 'size' key missing: %s" % query)
    assert "from" in query, (
                "query is malformed, 'from' key missing: %s" % query)

    # Searching for a term in a specific field and with a specific product
    params = {
        "for": "hang",
        "in": "dump",
        "search_mode": "contains",
        "product": "fennec"
    }
    params = sapi.SearchAPI.get_parameters(params)
    query = es.ElasticSearchAPI.build_query_from_params(params)
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
    Test ElasticSearchAPI.build_terms_query()

    """
    # Empty query
    fields = ""
    terms = None
    query = es.ElasticSearchAPI.build_terms_query(fields, terms)
    assert not query

    # Single term, single field query
    fields = "signature"
    terms = "hang"
    query = es.ElasticSearchAPI.build_terms_query(fields, terms)
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
    query = es.ElasticSearchAPI.build_terms_query(fields, terms)
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
    query = es.ElasticSearchAPI.build_terms_query(fields, terms)
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
    Test ElasticSearchAPI.build_wildcard_query()

    """
    # Empty query
    fields = ""
    terms = None
    query = es.ElasticSearchAPI.build_wildcard_query(fields, terms)
    assert not query, "Query is %s, null or empty expected." % query

    # Single term, single field query
    fields = "signature"
    terms = "hang"
    query = es.ElasticSearchAPI.build_wildcard_query(fields, terms)
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
    query = es.ElasticSearchAPI.build_wildcard_query(fields, terms)
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
    query = es.ElasticSearchAPI.build_wildcard_query(fields, terms)
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
    Test ElasticSearchAPI.format_versions()

    """
    # Empty versions
    versions = None
    versionstr = es.ElasticSearchAPI.format_versions(versions)
    assert not versionstr, (
                "The versions string is %s, null expected." % versionstr)

    # Only one product, no version
    versions = "firefox"
    versionstr = es.ElasticSearchAPI.format_versions(versions)
    assert versionstr == "product: firefox", (
                "Wrong formatting of versions for one product, no version: "
                "%s" % versionstr)

    # One product, one version
    versions = "firefox:5.0.1b"
    versionstr = es.ElasticSearchAPI.format_versions(versions)
    assert versionstr == "( product: firefox AND version: 5.0.1b )", (
                "Wrong formatting of versions for one product, one version: "
                "%s" % versionstr)

    # Multiple products, multiple versions
    versions = ["firefox:5.0.1b", "fennec:1", "test:abc"]
    versionstr = es.ElasticSearchAPI.format_versions(versions)
    expected = ("(( product: firefox AND version: 5.0.1b ) OR "
                "( product: fennec AND version: 1 ) OR "
                "( product: test AND version: abc ))")
    assert versionstr == expected, (
                "Wrong formatting of versions for multiple products, "
                "multiple versions: %s" % versionstr)


def test_prepare_terms():
    """
    Test ElasticSearchAPI.prepare_terms()

    """
    # Empty terms
    terms = ""
    search_mode = None
    newterms = es.ElasticSearchAPI.prepare_terms(terms, search_mode)
    assert not newterms, "Terms are %s, null or empty expected." % newterms

    # Contains mode, single term
    terms = "test"
    search_mode = "contains"
    newterms = es.ElasticSearchAPI.prepare_terms(terms, search_mode)
    assert newterms == terms.join(("*", "*")), (
                "Terms are not well prepared, missing stars around: %s" %
                newterms)

    # Contains mode, multiple terms
    terms = ["test", "hang"]
    search_mode = "contains"
    newterms = es.ElasticSearchAPI.prepare_terms(terms, search_mode)
    assert newterms == "*test hang*", (
                "Terms are not well prepared, missing stars around: %s" %
                newterms)

    # Starts with mode, multiple terms
    terms = ["test", "hang"]
    search_mode = "starts_with"
    newterms = es.ElasticSearchAPI.prepare_terms(terms, search_mode)
    assert newterms == "test hang*", (
                "Terms are not well prepared, missing stars after: %s" %
                newterms)

    # Is exactly mode, multiple terms
    terms = ["test", "hang"]
    search_mode = "is_exactly"
    newterms = es.ElasticSearchAPI.prepare_terms(terms, search_mode)
    assert newterms == " ".join(terms), (
                "Terms should be concatenated when using a is_exactly mode.")

    # Random unexisting mode, multiple terms
    terms = ["test", "hang"]
    search_mode = "random_unexisting_mode"
    newterms = es.ElasticSearchAPI.prepare_terms(terms, search_mode)
    assert newterms == terms, (
                "Terms should not be changed when using a mode other than "
                "is_exactly, starts_with or contains.")

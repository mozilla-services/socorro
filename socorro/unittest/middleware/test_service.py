import socorro.external.elasticsearch.elasticsearch as es
import socorro.external.postgresql.postgresql as pg
import socorro.middleware.service as serv
import socorro.lib.util as util


def get_dummy_context():
    """
    Create a dummy config object to use when testing.
    """
    context = util.DotDict()
    context.databaseHost = 'fred'
    context.databaseName = 'wilma'
    context.databaseUserName = 'ricky'
    context.databasePassword = 'lucy'
    context.databasePort = 127
    context.serviceImplementationModule = "socorro.external.elasticsearch"
    context.elasticSearchHostname = "localhost"
    context.elasticSearchPort = "9200"
    return context


def test_get_module():
    """
    Test Service.get_module
    """
    config = get_dummy_context()
    service = serv.DataAPIService(config)
    service.service_name = "search"
    params = {}

    # Test config module
    import_failed = False
    try:
        mod = service.get_module(params)
    except NotImplementedError:
        import_failed = True

    assert not import_failed, ("NotImplementedError exception raised when"
                               " trying to get config implementation")
    assert mod != False, "Result of get_module is not a module"

    try:
        search = mod.Search(config)
    except AttributeError:
        assert False, "The imported module does not contain the needed class"

    assert isinstance(search, es.ElasticSearchAPI), ("Imported module is not"
                                                     " the right one")

    # Test forced module
    import_failed = False
    params["force_api_impl"] = "postgresql"
    try:
        mod = service.get_module(params)
    except NotImplementedError:
        import_failed = True

    assert not import_failed, ("NotImplementedError exception raised when"
                               " trying to get config implementation")
    assert mod != False, "Result of get_module is not a module"

    try:
        search = mod.Search(config)
    except AttributeError:
        assert False, "The imported module does not contain the needed class"

    assert isinstance(search, pg.PostgresAPI), ("Imported module is not the "
                                                "right one")

    # Test default module
    import_failed = False
    params = {}
    service.default_service_order = [
        "socorro.external.elasticsearch",
        "socorro.external.postgresql",
    ]
    config.serviceImplementationModule = "unknownmodule"
    try:
        mod = service.get_module(params)
    except NotImplementedError:
        import_failed = True

    assert not import_failed, ("NotImplementedError exception raised when"
                               " trying to get config implementation")
    assert mod != False, "Result of get_module is not a module"

    try:
        search = mod.Search(config)
    except AttributeError:
        assert False, "The imported module does not contain the needed class"

    assert isinstance(search, es.ElasticSearchAPI), ("Imported module is not"
                                                     " the right one")

    # Test no valid module to import
    import_failed = False
    params = {}
    service.default_service_order = []
    config.serviceImplementationModule = "unknownmodule"
    try:
        mod = service.get_module(params)
    except NotImplementedError:
        import_failed = True

    assert import_failed, "Impossible import succeeded: %s" % mod

def test_parse_query_string():
    """
    Test Service.parse_query_string
    """
    config = get_dummy_context()
    service = serv.DataAPIService(config)

    # Test simple query string
    url = "param/value/"
    result = service.parse_query_string(url)
    expected = {
        "param": "value"
    }

    assert result == expected, "Parse error, expected: %s, returned: %s" % (
                               expected, result)

    # Test complex query string
    url = "product/firefox/from/yesterday/build/12+33+782/version/7.0.1b4/"
    result = service.parse_query_string(url)
    expected = {
        "product": "firefox",
        "from": "yesterday",
        "build": ["12", "33", "782"],
        "version": "7.0.1b4"
    }

    assert result == expected, "Parse error, expected: %s, returned: %s" % (
                               expected, result)

    # Test incorrect query string
    url = "product/firefox/for"
    result = service.parse_query_string(url)
    expected = {
        "product": "firefox"
    }

    assert result == expected, "Parse error, expected: %s, returned: %s" % (
                               expected, result)

    # Test empty value
    url = "product/firefox/for//"
    result = service.parse_query_string(url)
    expected = {
        "product": "firefox",
        "for": ""
    }

    assert result == expected, "Parse error, expected: %s, returned: %s" % (
                               expected, result)

    # Test empty param
    url = "product/firefox//bla/"
    result = service.parse_query_string(url)
    expected = {
        "product": "firefox"
    }

    assert result == expected, "Parse error, expected: %s, returned: %s" % (
                               expected, result)

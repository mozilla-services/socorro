# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import web
import cgi
import re

import socorro.lib.util as util
import socorro.database.database as db
import socorro.storage.crashstorage as cs
from socorro.external import (
    DatabaseError,
    InsertionError,
    MissingArgumentError,
    ResourceNotFound,
    BadArgumentError,
    ResourceUnavailable,
)

import raven

from configman import RequiredConfig


def typeConversion(type_converters, values_to_convert):
    """
    Convert a list of values into new types and return the new list.
    """
    return (t(v) for t, v in zip(type_converters, values_to_convert))


#==============================================================================
class BadRequest(web.webapi.HTTPError):
    """The only reason to override this exception class here instead of using
    the one in web.webapi is so that we can pass a custom message into the
    exception so the client can get a hint of what went wrong.
    """
    def __init__(self, message="bad request"):
        status = "400 Bad Request"
        if message and isinstance(message, dict):
            headers = {'Content-Type': 'application/json; charset=UTF-8'}
            message = json.dumps(message)
        else:
            headers = {'Content-Type': 'text/html'}
        super(BadRequest, self).__init__(status, headers, message)


#==============================================================================
class Timeout(web.webapi.HTTPError):
    """
    '408 Request Timeout' Error

    """
    def __init__(self, message="item currently unavailable"):
        status = "408 Request Timeout"
        if message and isinstance(message, dict):
            headers = {'Content-Type': 'application/json; charset=UTF-8'}
            message = json.dumps(message)
        else:
            headers = {'Content-Type': 'text/html'}
        super(Timeout, self).__init__(status, headers, message)


#==============================================================================
class NotFound(web.webapi.HTTPError):
    """Return a HTTPError with status code 404 and a description in JSON"""
    def __init__(self, message="Not found"):
        if isinstance(message, dict):
            message = json.dumps(message)
            headers = {'Content-Type': 'application/json; charset=UTF-8'}
        else:
            headers = {'Content-Type': 'text/html'}
        status = '404 Not Found'
        super(NotFound, self).__init__(status, headers, message)


#==============================================================================
class JsonWebServiceBase(RequiredConfig):

    """
    Provide an interface for JSON-based web services.

    """

    def __init__(self, config):
        """
        Set the DB and the pool up and store the config.
        """
        self.config = config

    def GET(self, *args):
        """
        Call the get method defined in a subclass and return its result.

        Return a JSON dump of the returned value,
        or the raw result if a content type was returned.

        """
        try:
            result = self.get(*args)
            if isinstance(result, tuple):
                web.header('Content-Type', result[1])
                return result[0]
            web.header('Content-Type', 'application/json')
            return json.dumps(result)
        except web.webapi.HTTPError:
            raise
        except (DatabaseError, InsertionError), e:
            raise web.webapi.InternalError(message=str(e))
        except (MissingArgumentError, BadArgumentError), e:
            raise BadRequest(str(e))
        except Exception:
            stringLogger = util.StringLogger()
            util.reportExceptionAndContinue(stringLogger)
            try:
                util.reportExceptionAndContinue(self.config.logger)
            except (AttributeError, KeyError):
                pass
            raise Exception(stringLogger.getMessages())

    def get(self, *args):
        raise NotImplementedError(
            "The GET function has not been implemented for %s" % repr(args)
        )

    def POST(self, *args):
        """
        Call the post method defined in a subclass and return its result.

        Return a JSON dump of the returned value,
        or the raw result if a content type was returned.

        """
        try:
            result = self.post(*args)
            if isinstance(result, tuple):
                web.header('Content-Type', result[1])
                return result[0]
            web.header('Content-Type', 'application/json')
            return json.dumps(result)
        except web.HTTPError:
            raise
        except (DatabaseError, InsertionError), e:
            raise web.webapi.InternalError(message=str(e))
        except (MissingArgumentError, BadArgumentError), e:
            raise BadRequest(str(e))
        except Exception:
            util.reportExceptionAndContinue(self.config.logger)
            raise

    def post(self, *args):
        raise NotImplementedError(
            "The POST function has not been implemented."
        )

    def PUT(self, *args):
        """
        Call the put method defined in a subclass and return its result.

        Return a JSON dump of the returned value,
        or the raw result if a content type was returned.

        """
        try:
            result = self.put(*args)
            if isinstance(result, tuple):
                web.header('Content-Type', result[1])
                return result[0]
            web.header('Content-Type', 'application/json')
            return json.dumps(result)
        except web.HTTPError:
            raise
        except Exception:
            util.reportExceptionAndContinue(self.config.logger)
            raise

    def put(self, *args):
        raise NotImplementedError("The PUT function has not been implemented.")


#==============================================================================
class JsonServiceBase(JsonWebServiceBase):

    """Provide an interface for JSON-based web services. For legacy services,
    to be removed when all services are updated.
    """

    def __init__(self, config):
        """
        Set the DB and the pool up and store the config.
        """
        super(JsonServiceBase, self).__init__(config)
        try:
            self.database = db.Database(config)
            self.crashStoragePool = cs.CrashStoragePool(
                config,
                storageClass=config.hbaseStorageClass
            )
        except (AttributeError, KeyError), x:
            self.config.logger.error(
                str(x),
                exc_info=True
            )


#------------------------------------------------------------------------------
# certain items in a URL path should NOT be split by `+`
DONT_TERM_SPLIT = re.compile("""
  \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}
""", re.VERBOSE)


#==============================================================================
class DataserviceWebServiceBase(JsonWebServiceBase):
    def __init__(self, config):
        namespace_name = self.__class__.__name__.split('.')[-1]
        self.config = config.services[namespace_name]
        #self.context = self.config

    #--------------------------------------------------------------------------
    def GET(self, *args, **kwargs):
        params = self._get_query_string_params()
        params.update(kwargs)
        if len(args) > 1:
            method_name = args[0]
            if method_name.startswith('get'):
                self.config.logger.error(
                    'The method %r does not exist on %r' %
                    (method_name, self)
                )
                raise web.webapi.NoMethod(self)
            method_name = 'get_' + method_name
        else:
            method_name = 'get'
        try:
            method = getattr(self, method_name)
        except AttributeError:
            self.config.logger.error(
                'The method %r does not exist on %r' %
                (method_name, self)
            )
            raise web.webapi.NoMethod(self)
        try:
            result = method(**params)
        except (MissingArgumentError, BadArgumentError), msg:
            raise BadRequest({
                'error': {
                    'message': str(msg)
                },
                'type': msg.__class__.__name__
            })
        except ResourceNotFound, msg:
            raise NotFound({
                'error': {
                    'message': str(msg)
                }
            })
        except ResourceUnavailable, msg:
            raise Timeout({
                'error': {
                    'message': str(msg)
                }
            })
        except Exception, msg:
            if self.config.sentry and self.config.sentry.dsn:
                client = raven.Client(dsn=self.config.sentry.dsn)
                identifier = client.get_ident(client.captureException())
                self.config.logger.info(
                    'Error captured in Sentry. Reference: %s' % identifier
                )
            raise

        if isinstance(result, tuple):
            web.header('Content-Type', result[1])
            return result[0]
        web.header('Content-Type', 'application/json')
        dumped = json.dumps(result)
        web.header('Content-Length', len(dumped))
        return dumped

    #--------------------------------------------------------------------------
    def POST(self, *args, **kwargs):
        # this is necessary in case some other method (e.g PUT) overrides
        # this method.
        params = self._get_web_input_params()
        data = web.data()
        if data:
            # If you post a payload as the body it gets picked up by
            # webapi in `web.data()` as a string.
            # It will also, rather annoyingly, make this data a key
            # in the output of `web.input()` which we also rely on.
            # So, in that case try to remove it as a key.
            try:
                params.pop(data)
            except KeyError:
                pass
            params['data'] = data
        try:
            result = self.post(**params)
        except (MissingArgumentError, BadArgumentError), msg:
            raise BadRequest({
                'error': {
                    'message': str(msg)
                }
            })
        except ResourceNotFound, msg:
            raise NotFound({
                'error': {
                    'message': str(msg)
                }
            })
        except ResourceUnavailable, msg:
            raise Timeout({
                'error': {
                    'message': str(msg)
                }
            })
        except Exception, msg:
            if self.config.sentry and self.config.sentry.dsn:
                client = raven.Client(dsn=self.config.sentry.dsn)
                identifier = client.get_ident(client.captureException())
                self.config.logger.info(
                    'Error captured in Sentry. Reference: %s' % identifier
                )
            raise
        if isinstance(result, tuple):
            web.header('Content-Type', result[1])
            return result[0]
        web.header('Content-Type', 'application/json')
        dumped = json.dumps(result)
        web.header('Content-Length', len(dumped))
        return dumped

    #--------------------------------------------------------------------------
    def PUT(self, *args, **kwargs):
        return self.POST(*args, **kwargs)

    #--------------------------------------------------------------------------
    def DELETE(self, *args, **kwargs):
        params = self._get_web_input_params()
        return self.delete(**params)

    #--------------------------------------------------------------------------
    def _get_query_string_params(self):
        params = {}
        query_string = web.ctx.query[1:]

        for key, values in cgi.parse_qs(query_string).items():
            if len(values) == 1:
                values = values[0]
            params[key] = values

        return params

    #--------------------------------------------------------------------------
    def _get_web_input_params(self, **extra):
        """Because of the stupidify of web.py we can't say that all just tell
        it to collect all POST or GET variables as arrays unless we explicitely
        list the defaults.

        So, try to look ahead at the class that will need the input and see
        if there are certain filters it expects to be lists.
        """
        defaults = {}
        for name, __, conversions in getattr(self.__class__, 'filters', []):
            if conversions[0] == 'list':
                defaults[name] = []
        if extra is not None:
            defaults.update(extra)
        return web.input(**defaults)

    #--------------------------------------------------------------------------
    def parse_url_path(self, path):
        """
        Take a string of parameters and return a dictionary of key, value.

        Example 1:
            "param/value/"
            =>
            {
                "param": "value"
            }

        Example 2:
            "param1/value1/param2/value21+value22+value23/"
            =>
            {
                "param1": "value1",
                "param2": [
                    "value21",
                    "value22",
                    "value23"
                ]
            }

        Example 3:
            "param1/value1/param2/"
            =>
            {
                "param1": "value1"
            }

        """
        terms_sep = "+"
        params_sep = "/"

        args = path.split(params_sep)

        params = {}
        for i in range(0, len(args), 2):
            try:
                if args[i]:
                    params[args[i]] = args[i + 1]
            except IndexError:
                pass

        for key, value in params.iteritems():
            if value.count(terms_sep) and not DONT_TERM_SPLIT.match(value):
                params[key] = value.split(terms_sep)

        return params

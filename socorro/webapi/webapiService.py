try:
    import json
except ImportError:
    import simplejson as json
import logging
import web

import socorro.lib.util as util
import socorro.database.database as db
import socorro.storage.crashstorage as cs


logger = logging.getLogger("webapi")


def typeConversion(type_converters, values_to_convert):
    """
    Convert a list of values into new types and return the new list.
    """
    return (t(v) for t, v in zip(type_converters, values_to_convert))


class Timeout(web.webapi.HTTPError):

    """
    '408 Request Timeout' Error

    """

    message = "item currently unavailable"

    def __init__(self):
        status = "408 Request Timeout"
        headers = {'Content-Type': 'text/html'}
        super(Timeout, self).__init__(self, status, headers, self.message)


class JsonWebServiceBase(object):

    """
    Provide an interface for JSON-based web services.

    """

    def __init__(self, config):
        """
        Set the DB and the pool up and store the config.
        """
        self.context = config

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
            return json.dumps(result)
        except web.webapi.HTTPError:
            raise
        except Exception:
            stringLogger = util.StringLogger()
            util.reportExceptionAndContinue(stringLogger)
            try:
                util.reportExceptionAndContinue(self.context.logger)
            except (AttributeError, KeyError):
                pass
            raise Exception(stringLogger.getMessages())

    def get(self, *args):
        raise NotImplementedError(
                    "The GET function has not been implemented for %s" % args)

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
            return json.dumps(result)
        except web.HTTPError:
            raise
        except Exception:
            util.reportExceptionAndContinue(self.context.logger)
            raise

    def post(self, *args):
        raise NotImplementedError(
                    "The POST function has not been implemented.")


class JsonServiceBase(JsonWebServiceBase):

    """
    Provide an interface for JSON-based web services.

    """

    def __init__(self, config):
        """
        Set the DB and the pool up and store the config.
        """
        super(JsonServiceBase, self).__init__(config)
        try:
            self.database = db.Database(config)
            self.crashStoragePool = cs.CrashStoragePool(config,
                                        storageClass=config.hbaseStorageClass)
        except (AttributeError, KeyError):
            util.reportExceptionAndContinue(logger)

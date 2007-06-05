from pylons import Response, c, g, cache, request, session
from pylons.controllers import WSGIController
from pylons.decorators import jsonify, validate
from pylons.templating import render, render_response
from pylons.helpers import abort, redirect_to, etag_cache
from pylons.i18n import N_, _, ungettext
from pylons import database
import socorro.models as model
import socorro.lib.helpers as h
import config

class BaseController(WSGIController):
    def __call__(self, environ, start_response):
        # Insert any code to be run per request here. The Routes match
        # is under environ['pylons.routes_dict'] should you want to check
        # the action or route vars here

        # hack alert. this should be in our conf file, but pylons
        # has a bug.
        #
        # See <http://groups.google.com/group/pylons-discuss/browse_thread/thread/747ac14d1e20f332/a650fb1011ec2387>
        #
        # for the gory details. Socorro Issue 38.
        #
        kwargs = {}
        uri, echo = database.get_engine_conf()
        kwargs['echo'] = echo
        database.get_engines()['%s|%s' % (uri, str(kwargs))] = \
          database.create_engine(uri, echo=echo,
                                 pool_recycle=config.processorConnTimeout) 
        return WSGIController.__call__(self, environ, start_response)

# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_') \
           or __name == '_']

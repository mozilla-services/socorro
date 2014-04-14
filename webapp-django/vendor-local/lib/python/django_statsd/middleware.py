from django_statsd.clients import statsd
import inspect
import time


class GraphiteMiddleware(object):

    def process_response(self, request, response):
        statsd.incr('response.%s' % response.status_code)
        if hasattr(request, 'user') and request.user.is_authenticated():
            statsd.incr('response.auth.%s' % response.status_code)
        return response

    def process_exception(self, request, exception):
        statsd.incr('response.500')
        if hasattr(request, 'user') and request.user.is_authenticated():
            statsd.incr('response.auth.500')


class GraphiteRequestTimingMiddleware(object):
    """statsd's timing data per view."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        view = view_func
        if not inspect.isfunction(view_func):
            view = view.__class__
        try:
            request._view_module = view.__module__
            request._view_name = view.__name__
            request._start_time = time.time()
        except AttributeError:
            pass

    def process_response(self, request, response):
        self._record_time(request)
        return response

    def process_exception(self, request, exception):
        self._record_time(request)

    def _record_time(self, request):
        if hasattr(request, '_start_time'):
            ms = int((time.time() - request._start_time) * 1000)
            data = dict(module=request._view_module, name=request._view_name,
                        method=request.method)
            statsd.timing('view.{module}.{name}.{method}'.format(**data), ms)
            statsd.timing('view.{module}.{method}'.format(**data), ms)
            statsd.timing('view.{method}'.format(**data), ms)


class TastyPieRequestTimingMiddleware(GraphiteRequestTimingMiddleware):
    """statd's timing specific to Tastypie."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            request._view_module = view_kwargs['api_name']
            request._view_name = view_kwargs['resource_name']
            request._start_time = time.time()
        except KeyError:
            pass

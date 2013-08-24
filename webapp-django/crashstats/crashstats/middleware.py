from django_statsd.clients import statsd


class AnalyticsMiddleware(object):
    """
    Middleware that counts how often each url is requested
    """

    def process_response(self, request, response):
        metric = "analytics.{0}.{1}.{2}".format(
            request.method,
            request.path_info.strip('/'),
            response.status_code
        )
        statsd.incr(metric)
        return response

from django_statsd.clients import statsd


class AnalyticsMiddleware(object):
    """
    Middleware that counts how often each url is requested
    """

    def process_response(self, request, response):
        path = request.path_info.lstrip('/').replace('.', '-')
        # avoid sending lots of low-volume or unique keys
        prefixes = ('rawdumps/', 'report/index/', 'report/pending/bp',
                    'report/pending/')

        for prefix in prefixes:
            if path.startswith(prefix):
                path = prefix
                break

        metric = "analytics.{0}.{1}.{2}".format(
            request.method,
            path,
            response.status_code
        )
        statsd.incr(metric)
        return response

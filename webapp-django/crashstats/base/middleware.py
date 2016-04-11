from session_csrf import CsrfMiddleware


class ExtendedCsrfMiddleware(CsrfMiddleware):
    """The only difference between this class and the base class
    from session_csrf is that it's possible to make it not set a
    cookie on the response. That basically makes it impossible to use
    CSRF but for certain requests that's perfectly fine.

    Note: The inbound cookie on the request is still valid and might
    help the user get additional access.

    The companion decorator to leverage this is
    crashstats.base.decorators.no_csrf_cookie
    Use that on your views and no anonymous CSRF cookie will be set
    on the response.
    """

    def process_response(self, request, response):
        if getattr(request, 'no_session_csrf_cookie', None):
            return response
        return super(ExtendedCsrfMiddleware, self).process_response(
            request, response
        )

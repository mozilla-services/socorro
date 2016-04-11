import functools


def no_csrf_cookie(view_func):
    """Use this to make sure our CSRF session middleware doesn't
    set a cookie."""

    @functools.wraps(view_func)
    def inner(request, *args, **kwargs):
        request.no_session_csrf_cookie = True
        return view_func(request, *args, **kwargs)
    return inner

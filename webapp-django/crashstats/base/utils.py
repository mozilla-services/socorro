from django.template import engines


def render_exception(exception):
    """When we need to render an exception as HTML.

    Often used to supply as the response body when there's a
    HttpResponseBadRequest.
    """
    template = engines['backend'].from_string(
        '<ul><li>{{ exception }}</li></ul>'
    )
    return template.render({'exception': exception})

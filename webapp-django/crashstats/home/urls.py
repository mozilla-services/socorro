from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(
        r'^product/(?P<product>\w+)$',
        views.home,
        name='home',
    ),

    # Redirect old home page to the new one.
    url(
        r'^products/(?P<product>\w+)$',
        views.LegacyHomeRedirectView.as_view()
    ),
    url(
        r'^products/(?P<product>\w+)/versions/(?P<versions>[;\w\.()]+)$',
        views.LegacyHomeRedirectView.as_view()
    ),
)

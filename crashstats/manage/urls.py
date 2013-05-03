from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url('^$',
        views.home,
        name='home'),
    url('^featured-versions/$',
        views.featured_versions,
        name='featured_versions'),
    url('^featured-versions/update/$',
        views.update_featured_versions,
        name='update_featured_versions'),
)

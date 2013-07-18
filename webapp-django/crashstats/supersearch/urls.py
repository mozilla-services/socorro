from django.conf.urls.defaults import patterns, url
from . import views

urlpatterns = patterns(
    '',
    url(r'^search/$',
        views.search,
        name='supersearch.search'),
    url(r'^search/results/$',
        views.search_results,
        name='supersearch.search_results'),
    url(r'^search/fields/$',
        views.search_fields,
        name='supersearch.search_fields'),
)

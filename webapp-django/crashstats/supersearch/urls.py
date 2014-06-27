from django.conf.urls import patterns, url
from . import views

urlpatterns = patterns(
    '',
    url(r'^search/$',
        views.search,
        name='supersearch.search'),
    url(r'^search/custom/$',
        views.search_custom,
        name='supersearch.search_custom'),
    url(r'^search/results/$',
        views.search_results,
        name='supersearch.search_results'),
    url(r'^search/query/$',
        views.search_query,
        name='supersearch.search_query'),
    url(r'^search/fields/$',
        views.search_fields,
        name='supersearch.search_fields'),
)

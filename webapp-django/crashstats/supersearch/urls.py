from django.conf.urls import url
from . import views

app_name='supersearch'
urlpatterns = [
    url(r'^search/$',
        views.search,
        name='search'),
    url(r'^search/custom/$',
        views.search_custom,
        name='search_custom'),
    url(r'^search/results/$',
        views.search_results,
        name='search_results'),
    url(r'^search/query/$',
        views.search_query,
        name='search_query'),
    url(r'^search/fields/$',
        views.search_fields,
        name='search_fields'),
]

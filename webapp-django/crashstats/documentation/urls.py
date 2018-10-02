from django.conf.urls import url
from . import views


app_name = 'documentation'
urlpatterns = [
    url(
        r'^supersearch/$',
        views.supersearch_home,
        name='supersearch_home',
    ),
    url(
        r'^supersearch/examples/$',
        views.supersearch_examples,
        name='supersearch_examples',
    ),
    url(
        r'^supersearch/api/$',
        views.supersearch_api,
        name='supersearch_api',
    ),
    url(
        r'^memory_dump_access/$',
        views.memory_dump_access,
        name='memory_dump_access',
    ),
    url(
        r'^products/$',
        views.products,
        name='products',
    ),
    url(
        r'^$',
        views.home,
        name='home',
    ),
]

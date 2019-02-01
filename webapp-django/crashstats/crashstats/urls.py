from django.conf import settings
from django.conf.urls import url
from django.views.generic import RedirectView

from crashstats.crashstats import views


products = r'/products/(?P<product>\w+)'
versions = r'/versions/(?P<versions>[;\w\.()]+)'
version = r'/versions/(?P<version>[;\w\.()]+)'

perm_legacy_redirect = settings.PERMANENT_LEGACY_REDIRECTS


app_name = 'crashstats'
urlpatterns = [
    url(r'^robots\.txt$',
        views.robots_txt,
        name='robots_txt'),

    # DEPRECATED(willkg): This endpoint should be deprecated in
    # favor of the dockerflow /__version__ one
    url(r'^status/json/$',
        views.status_json,
        name='status_json'),

    url(r'^report/index/(?P<crash_id>[\w-]+)$',
        views.report_index,
        name='report_index'),
    url(r'^search/quick/$',
        views.quick_search,
        name='quick_search'),
    url(r'^buginfo/bug', views.buginfo,
        name='buginfo'),
    url(r'^rawdumps/(?P<crash_id>[\w-]{36})-(?P<name>\w+)\.(?P<extension>json|dmp|json\.gz)$',
        views.raw_data,
        name='raw_data_named'),
    url(r'^rawdumps/(?P<crash_id>[\w-]{36}).(?P<extension>json|dmp)$',
        views.raw_data,
        name='raw_data'),
    url(r'^login/$',
        views.login,
        name='login'),
    url(r'^about/throttling/$',
        views.about_throttling,
        name='about_throttling'),
    url(r'^home/product/(?P<product>\w+)$',
        views.product_home,
        name='product_home'),

    # Home page
    url(r'^$',
        views.home,
        name='home'),

    # Dockerflow endpoints
    url(r'__version__',
        views.dockerflow_version,
        name='dockerflow_version'),

    # redirect deceased Advanced Search URL to Super Search
    url(r'^query/$',
        RedirectView.as_view(
            url='/search/',
            query_string=True,
            permanent=True
        )),

    # Redirect old independant pages to the unified Profile page.
    url(r'^your-crashes/$',
        RedirectView.as_view(
            url='/profile/',
            permanent=perm_legacy_redirect
        )),
    url(r'^permissions/$',
        RedirectView.as_view(
            url='/profile/',
            permanent=perm_legacy_redirect
        )),
]

from django.conf.urls import url
from django.views.generic import RedirectView
from django.conf import settings

from . import views


products = r'/products/(?P<product>\w+)'
versions = r'/versions/(?P<versions>[;\w\.()]+)'
version = r'/versions/(?P<version>[;\w\.()]+)'

perm_legacy_redirect = settings.PERMANENT_LEGACY_REDIRECTS


app_name = 'crashstats'
urlpatterns = [
    url('^robots\.txt$',
        views.robots_txt,
        name='robots_txt'),

    # DEPRECATED(willkg): This endpoint should be deprecated in
    # favor of the dockerflow /__version__ one
    url(r'^status/json/$',
        views.status_json,
        name='status_json'),

    url(r'^crontabber-state/$',
        views.crontabber_state,
        name='crontabber_state'),
    url(r'^exploitability/$',
        views.exploitability_report,
        name='exploitability_report'),
    url(r'^report/index/(?P<crash_id>[\w-]+)$',
        views.report_index,
        name='report_index'),
    url(r'^report/index/(?P<crash_id>[\w-]+)/new$',
        views.new_report_index,
        name='new_report_index'),
    url(r'^search/quick/$',
        views.quick_search,
        name='quick_search'),
    url(r'^buginfo/bug', views.buginfo,
        name='buginfo'),
    url(r'^rawdumps/(?P<crash_id>[\w-]{36})-(?P<name>\w+)\.'
        r'(?P<extension>json|dmp|json\.gz)$',
        views.raw_data,
        name='raw_data_named'),
    url(r'^rawdumps/(?P<crash_id>[\w-]{36}).(?P<extension>json|dmp)$',
        views.raw_data,
        name='raw_data'),
    url(r'^login/$',
        views.login,
        name='login'),
    url(r'^graphics_report/$',
        views.graphics_report,
        name='graphics_report'),
    url(r'^about/throttling/$',
        views.about_throttling,
        name='about_throttling'),

    # Dockerflow endpoints
    url(r'__version__',
        views.dockerflow_version,
        name='dockerflow_version'),

    # if we do a permanent redirect, the browser will "cache" the redirect and
    # it will make it very hard to ever change the DEFAULT_PRODUCT
    url(r'^$',
        RedirectView.as_view(
            url='/home/product/%s' % settings.DEFAULT_PRODUCT,
            permanent=False  # this is not a legacy URL
        )),

    # redirect deceased Advanced Search URL to Super Search
    url(r'^query/$',
        RedirectView.as_view(
            url='/search/',
            query_string=True,
            permanent=True
        )),

    # redirect deceased Report List URL to Signature report
    url(r'^report/list$',
        RedirectView.as_view(
            pattern_name='signature:signature_report',
            query_string=True,
            permanent=True
        )),

    # redirect deceased Daily Crashes URL to Mission Control
    url(r'^daily$',
        RedirectView.as_view(
            url="https://missioncontrol.telemetry.mozilla.org/#/",
            permanent=True
        )),
    url('^crashes-per-day/$',
        RedirectView.as_view(
            url="https://missioncontrol.telemetry.mozilla.org/#/",
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

    # handle old-style URLs
    url(r'^products/(?P<product>\w+)/$',
        RedirectView.as_view(
            url='/home/products/%(product)s',
            permanent=perm_legacy_redirect
        )),
    url(r'^products/(?P<product>\w+)/versions/(?P<versions>[;\w\.()]+)/$',
        RedirectView.as_view(
            url='/home/products/%(product)s/versions/%(versions)s',
            permanent=perm_legacy_redirect
        )),
    url('^home' + products + '/versions/$',
        RedirectView.as_view(
            url='/home/products/%(product)s',
            permanent=perm_legacy_redirect
        )),
]

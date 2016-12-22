from django.conf.urls import patterns, url
from django.views.generic import RedirectView
from django.conf import settings

from . import views


products = r'/products/(?P<product>\w+)'
versions = r'/versions/(?P<versions>[;\w\.()]+)'
version = r'/versions/(?P<version>[;\w\.()]+)'

perm_legacy_redirect = settings.PERMANENT_LEGACY_REDIRECTS


urlpatterns = patterns(
    '',  # prefix
    url('^robots\.txt$',
        views.robots_txt,
        name='robots_txt'),
    url(r'^status/json/$',
        views.status_json,
        name='status_json'),
    url(r'^status/revision/$',
        views.status_revision,
        name='status_revision'),
    url(r'^crontabber-state/$',
        views.crontabber_state,
        name='crontabber_state'),
    url('^crashes-per-day/$',
        views.crashes_per_day,
        name='crashes_per_day'),
    # handle old-style urls
    url(r'^report/exploitability/$',
        views.exploitable_crashes,
        name='exploitable_crashes_legacy'),
    url(r'^report/exploitability' + products + versions + '$',
        views.exploitable_crashes,
        name='exploitable_crashes'),
    url(r'^report/exploitability' + products + '/?$',
        views.exploitable_crashes,
        name='exploitable_crashes'),
    url(r'^exploitability/$',
        views.exploitability_report,
        name='exploitability_report'),
    url(r'^report/index/(?P<crash_id>[\w-]+)$',
        views.report_index,
        name='report_index'),
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
    url(r'^nightlies_for_product/json_data$',
        views.get_nightlies_for_product_json,
        name='get_nightlies_for_product_json'),
    url(r'^gccrashes' + products + '$',
        views.gccrashes,
        name='gccrashes'),
    url(r'^gccrashes' + products + version + '$',
        views.gccrashes,
        name='gccrashes'),
    url(r'^gccrashes/json_data$',
        views.gccrashes_json,
        name='gccrashes_json'),
    url(r'^login/$',
        views.login,
        name='login'),
    url(r'^graphics_report/$',
        views.graphics_report,
        name='graphics_report'),
    url(r'^about/throttling/$',
        views.about_throttling,
        name='about_throttling'),

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

    # redirect deceased Daily Crashes URL to Crasher per Day
    url(r'^daily$',
        RedirectView.as_view(
            pattern_name='crashstats:crashes_per_day',
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

    # Redirect deleted status page to monitoring page.
    url(
        r'^status/$',
        RedirectView.as_view(
            pattern_name='monitoring:index',
            permanent=not settings.DEBUG,
        ),
        name='status_redirect',
    ),

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
)

from django.conf.urls import patterns, url
from django.views.generic import RedirectView
from django.conf import settings

from . import views

products = r'/products/(?P<product>\w+)'
versions = r'/versions/(?P<versions>[;\w\.()]+)'
version = r'/versions/(?P<version>[;\w\.()]+)'
crash_type = r'/crash_type/(?P<crash_type>\w+)'
start_date = r'/start_date/(?P<start_date>[0-9]{4}-[0-9]{2}-[0-9]{2})'
end_date = r'/end_date/(?P<end_date>[0-9]{4}-[0-9]{2}-[0-9]{2})'
date_range_type = r'/date_range_type/(?P<date_range_type>\w+)'
# putting a * on the following regex so we allow URLs to be things like
# `.../os_name/` without any default value which the view function will
# take care of anyway
os_name = r'/os_name/(?P<os_name>[\w\s]*)'
result_count = r'/result_count/(?P<result_count>\d+)'
perm_legacy_redirect = settings.PERMANENT_LEGACY_REDIRECTS
report_list_partials = (
    'reports|comments|sigurls|bugzilla|table|correlations|graph'
)

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
    url('^topcrasher' + products + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + date_range_type + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + date_range_type +
        crash_type + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + date_range_type +
        crash_type + os_name + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + date_range_type +
        crash_type + os_name + result_count + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + crash_type + os_name + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + crash_type + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + os_name + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^daily$',
        views.daily,
        name='daily'),
    url('^crashes-per-day/$',
        views.crashes_per_day,
        name='crashes_per_day'),
    # handle old-style urls
    url(r'^report/list$',
        views.report_list,
        name='report_list'),
    url(r'^report/list/partials/(?P<partial>%s)/$' % report_list_partials,
        views.report_list,
        name='report_list_partial'),
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
    url(r'^topcrasher/plot_signature/(?P<product>\w+)/(?P<versions>[;\w\.()]+)'
        r'/(?P<start_date>[0-9]{4}-[0-9]{2}-[0-9]{2})/'
        r'(?P<end_date>[0-9]{4}-[0-9]{2}-[0-9]{2})/(?P<signature>.*)',
        views.plot_signature,
        name='plot_signature'),
    url(r'^signature_summary/$',
        views.signature_summary,
        name='signature_summary'),
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
    url(r'^correlation/signatures$',
        views.correlations_signatures_json,
        name='correlations_signatures_json'),
    url(r'^correlations/$',
        views.correlations_json,
        name='correlations_json'),
    url(r'^correlations/count/$',
        views.correlations_count_json,
        name='correlations_count_json'),
    url(r'^gccrashes' + products + '$',
        views.gccrashes,
        name='gccrashes'),
    url(r'^gccrashes' + products + version + '$',
        views.gccrashes,
        name='gccrashes'),
    url(r'^gccrashes/json_data$',
        views.gccrashes_json,
        name='gccrashes_json'),
    url(r'^adu_by_signature/json_data$',
        views.adu_by_signature_json,
        name='adu_by_signature_json'),
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

    # redirect deceased Advanced Search URLs to Super Search
    url(r'^query/$',
        RedirectView.as_view(
            url='/search/',
            query_string=True,
            permanent=True
        )),

    # Redirect from the old name "Crashes per User" to "Crashes per Day"
    url(
        r'^crashes-per-user/$',
        RedirectView.as_view(
            pattern_name='crashstats:crashes_per_day',
            query_string=True,
            # At some point in 2018, we can confidently change this to:
            # `permanent=True` when we know the redirect is working correctly.
            # In the transition time, it's safer to use a temporary redirect
            # since permanent redirects tend to get very stuck in the brower.
            permanent=not settings.DEBUG,
        ),
        name='crashes_per_user_redirect',
    ),

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
    url(r'^topcrasher/byversion/(?P<product>\w+)/(?P<versions>[;\w\.()]+)$',
        RedirectView.as_view(
            url='/topcrasher/products/%(product)s/versions/%(versions)s',
            permanent=perm_legacy_redirect
        )),
    url(r'^topcrasher' + products + '/versions/$',
        RedirectView.as_view(
            url='/topcrasher/products/%(product)s',
            permanent=perm_legacy_redirect
        )),
    url('^home' + products + '/versions/$',
        RedirectView.as_view(
            url='/home/products/%(product)s',
            permanent=perm_legacy_redirect
        )),
)

from django.conf.urls.defaults import patterns, url
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
    url('^favicon\.ico$',
        views.favicon_ico,
        name='favicon_ico'),
    url('^robots\.txt$',
        views.robots_txt,
        name='robots_txt'),
    url('^home' + products + '$',
        views.home,
        name='home'),
    url('^home' + products + versions + '$',
        views.home,
        name='home'),
    url(r'^home/frontpage_json$',
        views.frontpage_json,
        name='frontpage_json'),
    url(r'^status/$',
        views.status,
        name='status'),
    url(r'^status/json/$',
        views.status_json,
        name='status_json'),
    url(r'^status/revision/$',
        views.status_revision,
        name='status_revision'),
    url(r'^crontabber-state/$',
        views.crontabber_state,
        name='crontabber_state'),
    url(r'^crontabber-state/data.json$',
        views.crontabber_state_json,
        name='crontabber_state_json'),
    url(r'^your-crashes/$',
        views.your_crashes,
        name='your_crashes'),
    url(r'^products/$',
        views.products_list,
        name='products_list'),
    url('^topcrasher' + products + '$',
        views.topcrasher,
        name='topcrasher'),
    url('^topcrasher' + products + versions + '$',
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
    url(r'^topcrasher_ranks_bybug/$',
        views.topcrasher_ranks_bybug,
        name='topcrasher_ranks_bybug'),
    url('^explosive/$',
        views.explosive,
        name='explosive'),
    url('^explosive' + products + '$',
        views.explosive,
        name='explosive'),
    url('^explosive' + products + versions + '$',
        views.explosive,
        name='explosive'),
    url('^explosive-data/signature/(?P<signature>.+)'
        '/date/(?P<date>\d{4}-\d{2}-\d{2})/?$',
        views.explosive_data,
        name='explosive_data'),
    url('^daily$',
        views.daily,
        name='daily'),
    # handle old-style urls
    url('^topchangers' + products + '$',
        views.topchangers,
        name='topchangers'),
    url('^topchangers' + products + versions + '$',
        views.topchangers,
        name='topchangers'),
    url('^topchangers' + products + versions + '$',
        views.topchangers,
        name='topchangers'),
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
    url(r'^report/index/(?P<crash_id>.*)$',
        views.report_index,
        name='report_index'),
    # make the suffix `_ajax` optional there.
    # we prefer report/pending/XXX but because of legacy we need to
    # support report/pending_ajax/XXX too
    url(r'^report/pending(_ajax)?/(?P<crash_id>.*)$',
        views.report_pending,
        name='report_pending'),
    url(r'^query/$',
        views.query,
        name='query'),
    url(r'^query/query$',
        RedirectView.as_view(
            permanent=perm_legacy_redirect,
            query_string=True,
            url='/query/'
        )),
    url(r'^buginfo/bug', views.buginfo,
        name='buginfo'),
    url(r'^topcrasher/plot_signature/(?P<product>\w+)/(?P<versions>[;\w\.()]+)'
        r'/(?P<start_date>[0-9]{4}-[0-9]{2}-[0-9]{2})/'
        r'(?P<end_date>[0-9]{4}-[0-9]{2}-[0-9]{2})/(?P<signature>.*)',
        views.plot_signature,
        name='plot_signature'),
    url(r'^signature_summary/json_data$',
        views.signature_summary,
        name='signature_summary'),
    url(r'^rawdumps/(?P<crash_id>[\w-]{36}).(?P<extension>json|dmp)$',
        views.raw_data,
        name='raw_data'),
    url(r'^crash_trends' + products + '$',
        views.crash_trends,
        name='crash_trends'),
    url(r'^crash_trends' + products + versions + '$',
        views.crash_trends,
        name='crash_trends'),
    url(r'^crash_trends/json_data$',
        views.crashtrends_json,
        name='crashtrends_json'),
    url(r'^nightlies_for_product/json_data$',
        views.get_nightlies_for_product_json,
        name='get_nightlies_for_product_json'),
    url(r'^correlation$',
        views.correlations_json,
        name='correlations_json'),
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
    url(r'^permissions/$',
        views.permissions,
        name='permissions'),
    # if we do a permanent redirect, the browser will "cache" the redirect and
    # it will make it very hard to ever change the DEFAULT_PRODUCT
    url(r'^$',
        RedirectView.as_view(
            url='/home/products/%s' % settings.DEFAULT_PRODUCT,
            permanent=False  # this is not a legacy URL
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
    url(r'^products/(?P<product>\w+)/versions/(?P<versions>[;\w\.()]+)/'
        r'topchangers$',
        RedirectView.as_view(
            url='/topchangers/products/%(product)s',
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
    url(r'^topchangers' + products + '/versions/$',
        RedirectView.as_view(
            url='/topchangers/products/%(product)s',
            permanent=perm_legacy_redirect
        )),
    url('^home' + products + '/versions/$',
        RedirectView.as_view(
            url='/home/products/%(product)s',
            permanent=perm_legacy_redirect
        )),
)

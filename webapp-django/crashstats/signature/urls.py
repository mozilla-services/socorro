from django.conf.urls import patterns, url
from . import views


urlpatterns = patterns(
    '',
    url(
        r'^reports/$',
        views.signature_reports,
        name='signature_reports',
    ),
    url(
        r'^comments/$',
        views.signature_comments,
        name='signature_comments',
    ),
    url(
        r'^correlations/$',
        views.signature_correlations,
        name='signature_correlations',
    ),
    url(
        r'^graphdata/(?P<channel>\w+)/$',
        views.signature_graph_data,
        name='signature_graph_data',
    ),
    url(
        r'^aggregation/(?P<aggregation>\w+)/$',
        views.signature_aggregation,
        name='signature_aggregation',
    ),
    url(
        r'^graphs/(?P<field>\w+)/$',
        views.signature_graphs,
        name='signature_graphs',
    ),
    url(
        r'^summary/$',
        views.signature_summary,
        name='signature_summary',
    ),
    url(
        r'^bugzilla/$',
        views.signature_bugzilla,
        name='signature_bugzilla',
    ),
    url(
        r'^$',
        views.signature_report,
        name='signature_report',
    ),
)

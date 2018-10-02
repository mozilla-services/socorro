from django.conf.urls import url
from . import views


app_name = 'signature'
urlpatterns = [
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
]

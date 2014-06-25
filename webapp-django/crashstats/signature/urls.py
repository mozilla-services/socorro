from django.conf.urls.defaults import patterns, url
from . import views


urlpatterns = patterns(
    '',
    url(
        r'^reports/$',
        views.signature_reports,
        name='signature_reports',
    ),
    url(
        r'^aggregation/(?P<aggregation>\w+)/$',
        views.signature_aggregation,
        name='signature_aggregation',
    ),
    url(
        r'^$',
        views.signature_report,
        name='signature_report',
    ),
)

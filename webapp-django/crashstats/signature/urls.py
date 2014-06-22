from django.conf.urls.defaults import patterns, url
from . import views


signature_pattern = r'(?P<signature>.*)'

urlpatterns = patterns(
    '',
    url(
        '^' + signature_pattern + '/reports/$',
        views.signature_reports,
        name='signature_reports',
    ),
    url(
        '^' + signature_pattern + r'/aggregation/(?P<aggregation>\w+)/$',
        views.signature_aggregation,
        name='signature_aggregation',
    ),
    url(
        '^' + signature_pattern + '/$',
        views.signature_report,
        name='signature_report',
    ),
)

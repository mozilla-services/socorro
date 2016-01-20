from django.conf.urls import patterns, url
from . import views


urlpatterns = patterns(
    '',
    url(r'^$',
        views.index,
        name='index'),
    url(r'^crash-analysis-health/$',
        views.crash_analysis_health,
        name='crash_analysis_health'),
    url(r'^crontabber/$',
        views.crontabber_status,
        name='crontabber_status'),
    url(r'^healthcheck/$',
        views.healthcheck,
        name='healthcheck'),
)

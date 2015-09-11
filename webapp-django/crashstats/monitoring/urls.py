from django.conf.urls import patterns, url
from . import views


urlpatterns = patterns(
    '',
    url(r'^crash-analysis-health/$',
        views.crash_analysis_health,
        name='crash_analysis_health'),
)

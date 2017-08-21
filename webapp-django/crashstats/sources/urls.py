from django.conf.urls import patterns, url
from . import views


urlpatterns = patterns(
    '',
    url(r'^highlight/$',
        views.highlight_url,
        name='highlight_url'),
)

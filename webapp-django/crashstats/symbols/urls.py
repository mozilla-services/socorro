from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',  # prefix
    url('^$', views.home, name='home'),
    url('^upload/?$', views.upload, name='upload'),
    url('^upload/web/$', views.web_upload, name='web_upload'),
    url('^upload/api/$', views.api_upload, name='api_upload'),
    url('^upload/(?P<pk>\d+)/download/$', views.download, name='download'),
    url('^upload/(?P<pk>\d+)/preview/$', views.preview, name='preview'),
)

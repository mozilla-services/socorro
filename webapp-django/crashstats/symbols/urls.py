from django.conf.urls import url

from . import views


urlpatterns = [
    url('^$', views.home, name='home'),
    url('^upload/?$', views.upload, name='upload'),
    url('^upload/web/$', views.web_upload, name='web_upload'),
    url('^upload/api/$', views.api_upload, name='api_upload'),
    url('^upload/(?P<pk>\d+)/content/$', views.content, name='content'),
]

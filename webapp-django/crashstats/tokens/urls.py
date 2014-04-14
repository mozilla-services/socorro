from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns(
    '',  # prefix
    url('^$', views.home, name='home'),
    url('^delete/(?P<pk>\d+)/$', views.delete_token, name='delete_token'),
)

from django.conf.urls.defaults import *

from . import views


urlpatterns = patterns(
    '',
    url(r'^$', views.home, name='bixie.home'),
    url(r'^reports/list$', views.list, name='bixie.list'),
)

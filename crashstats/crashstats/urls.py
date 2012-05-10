from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to
from . import views


urlpatterns = patterns('',
    url(r'^products/\w+$', views.home, name='crashstats.products'),
    url(r'^$', redirect_to, {'url': '/products/Firefox'}),
)

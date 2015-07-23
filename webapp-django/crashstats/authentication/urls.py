from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',  # prefix
    url('^_debug_login/$', views.debug_login, name='debug_login'),
)

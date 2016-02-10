from django.conf.urls import patterns, url
from . import views


urlpatterns = patterns(
    '',
    url(
        r'^products/(?P<product>\w+)$',
        views.home,
        name='home',
    ),
)

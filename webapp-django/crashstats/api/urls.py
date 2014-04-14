from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns(
    '',  # prefix
    url('^$', views.documentation, name='documentation'),
    url('^(?P<model_name>\w+)/$',
        views.model_wrapper,
        name='model_wrapper'),
)

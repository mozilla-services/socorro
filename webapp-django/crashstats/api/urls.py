from django.conf.urls import url

from . import views


urlpatterns = [
    url('^$', views.documentation, name='documentation'),
    url('^(?P<model_name>\w+)/$',
        views.model_wrapper,
        name='model_wrapper'),
]

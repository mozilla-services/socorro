from django.conf.urls import url

from . import views


urlpatterns = [
    url('^$', views.home, name='home'),
    url('^delete/(?P<pk>\d+)/$', views.delete_token, name='delete_token'),
]

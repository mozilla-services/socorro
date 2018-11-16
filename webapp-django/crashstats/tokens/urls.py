from django.conf.urls import url

from crashstats.tokens import views


app_name = 'tokens'
urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^delete/(?P<pk>\d+)/$', views.delete_token, name='delete_token'),
]

from django.conf.urls import url

from crashstats.graphics import views

app_name = 'graphics'
urlpatterns = [
    url(r'^graphics_report/$', views.graphics_report, name='report'),
]

from django.conf.urls import url

from crashstats.profile import views


app_name = 'profile'
urlpatterns = [
    url(
        r'^$',
        views.profile,
        name='profile',
    ),
]

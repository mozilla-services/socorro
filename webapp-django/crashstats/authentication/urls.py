from django.conf.urls import url

from . import views


urlpatterns = [
    url(
        '^_debug_login/$',
        views.debug_login,
        name='debug_login'
    ),
    url(
        '^oauth2/signout/$',
        views.oauth2_signout,
        name='oauth2_signout'
    ),
    url(
        '^oauth2/signin/$',
        views.oauth2_signin,
        name='oauth2_signin'
    ),
]

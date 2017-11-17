from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^highlight/$',
        views.highlight_url,
        name='highlight_url'),
]

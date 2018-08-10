from django.conf.urls import url

from . import views


app_name = 'home'
urlpatterns = [
    url(
        r'^product/(?P<product>\w+)$',
        views.product_home,
        name='product_home',
    ),

    # Redirect old home page to the new one.
    url(
        r'^products/(?P<product>\w+)$',
        views.LegacyHomeRedirectView.as_view()
    ),
    url(
        r'^products/(?P<product>\w+)/versions/(?P<versions>[;\w\.()]+)$',
        views.LegacyHomeRedirectView.as_view()
    ),
]

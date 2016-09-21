from django.conf.urls import url

from .views import unique_link

urlpatterns = [
    url(r'^ligilo/(?P<token>[\w\.-_]+)', unique_link, name='unique_link')
]

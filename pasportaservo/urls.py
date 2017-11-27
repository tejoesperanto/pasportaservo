from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView


urlpatterns = [
    url('', include('core.urls')),
    url(_(r'^management/'), admin.site.urls),
    url(_(r'^messages/'), include('postman.urls', namespace='postman', app_name='postman')),
    url('', include('hosting.urls')),
    url('', include('pages.urls')),
    url('', include('links.urls')),
    url(_(r'^blog/'), include('blog.urls', namespace='blog')),
    url(r'^mapo/', include('maps.urls')),
]

handler403 = 'pasportaservo.views.custom_permission_denied_view'

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', debug_toolbar.urls),
    ]

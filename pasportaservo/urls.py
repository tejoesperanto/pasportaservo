from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from .views import ExtendedWriteView

urlpatterns = [
    url('', include('core.urls')),
    url(_(r'^management/'), admin.site.urls),
    url(_(r'^messages/'), include('postman.urls', namespace='postman')),
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
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

url_index_postman = '/'.join([reverse_lazy('postman:inbox').rstrip('/').rsplit('/', maxsplit=1)[0], ''])
url_index_maps = reverse_lazy('world_map')
url_index_debug = '/__debug__/'

for module in (m for m in urlpatterns if m.app_name == 'postman'):
    for pattern in (p for p in module.url_patterns if p.name == 'write'):
        pattern.callback = ExtendedWriteView.as_view()

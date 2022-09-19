from django.conf import settings
from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.urls.resolvers import URLPattern
from django.utils.translation import pgettext_lazy

from .views import (
    ExtendedConversationView, ExtendedMessageView,
    ExtendedReplyView, ExtendedWriteView,
)

urlpatterns = [
    path('', include('core.urls')),
    path(pgettext_lazy("URL", 'management/'), admin.site.urls),
    path(pgettext_lazy("URL", 'messages/'), include('postman.urls', namespace='postman')),
    path('', include('hosting.urls')),
    path('', include('pages.urls')),
    path('', include('links.urls')),
    path(pgettext_lazy("URL", 'blog/'), include('blog.urls', namespace='blog')),
    path(pgettext_lazy("URL", 'map/'), include('maps.urls')),
]

handler403 = 'pasportaservo.views.custom_permission_denied_view'

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

url_index_postman = '/'.join([reverse_lazy('postman:inbox').rstrip('/').rsplit('/', maxsplit=1)[0], ''])
url_index_maps = reverse_lazy('world_map')
url_index_debug = '/__debug__/'

for module in (m for m in urlpatterns if m.app_name == 'postman'):
    for pattern in (
            p for p in module.url_patterns
            if isinstance(p, URLPattern) and p.name in ['write', 'reply', 'view', 'view_conversation']
    ):
        # TODO: clean up this quick-and-dirty hack, during the chat overhaul.
        pattern.callback = {
            'write': ExtendedWriteView,
            'reply': ExtendedReplyView,
            'view': ExtendedMessageView,
            'view_conversation': ExtendedConversationView,
        }[pattern.name].as_view()

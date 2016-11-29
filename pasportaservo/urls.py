from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _


urlpatterns = [
    url('', include('core.urls')),
    url(_(r'^admin/'), admin.site.urls),
    url(_(r'^messages/'), include('postman.urls', namespace='postman', app_name='postman')),
    url('', include('hosting.urls')),
    url('', include('pages.urls')),
    url('', include('book.urls')),
    url('', include('links.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

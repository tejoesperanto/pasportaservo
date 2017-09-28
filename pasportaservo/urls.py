from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView


urlpatterns = [
    url('', include('core.urls')),
    url(_(r'^admin/'), admin.site.urls),
    url(_(r'^messages/'), include('postman.urls', namespace='postman', app_name='postman')),
    url(_(r'^blog/'), include('blog.urls', namespace='blog')),
    url(r'^mapo/', include('maps.urls')),
    url('', include('hosting.urls')),
    url('', include('pages.urls')),
    url('', include('links.urls')),
]

handler403 = 'pasportaservo.debug.custom_permission_denied_view'

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]


urlpatterns += [
    url(r'^editor/$', TemplateView.as_view(
        template_name="editor.html"
    ), name='editor'),
]

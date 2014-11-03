from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

urlpatterns = patterns('hosting.views',
    url(r'^$', 'home', name='home'),
    url(_(r'^register/$'), 'register', name='register'),
    url(_(r'^profile/create/$'), 'profile_create', name='profile_create'),
    url(_(r'^profile/$'), 'profile_detail', name='profile_detail'),
    url(_(r'^profile/update/$'), 'profile_update', name='profile_update'),
    url(_(r'^profile/delete/$'), 'profile_delete', name='profile_delete'),

    url(_(r'^place/(?P<pk>\d+)/$'), 'place_detail', name='place_detail'),
    url(_(r'^place/create/$'), 'place_create', name='place_create'),
    url(_(r'^place/(?P<pk>\d+)/update/$'), 'place_update', name='place_update'),
    url(_(r'^place/(?P<pk>\d+)/delete/$'), 'place_delete', name='place_delete'),
    url(_(r'^place/(?P<pk>\d+)/authorized/$'), 'authorized_users', name='authorized_users'),
    url(_(r'^place/(?P<pk>\d+)/authorize/$'), 'authorize_user', name='authorize_user'),
    url(_(r'^place/(?P<pk>\d+)/authorize/(?P<user>\w+)/$'), 'authorize_user_link', name='authorize_user_link'),

    url(_(r'^phone/create/$'), 'phone_create', name='phone_create'),
    url(_(r'^phone/(?P<num>\w+)/update/$'), 'phone_update', name='phone_update'),
    url(_(r'^phone/(?P<num>\w+)/delete/$'), 'phone_delete', name='phone_delete'),

    url(_(r'^search/$'), 'search', name='search'),
)

if settings.DEBUG:
    urlpatterns += patterns('django.views.static',
        url(r'media/(?P<path>.*)', 'serve', {'document_root': settings.MEDIA_ROOT}),
    )

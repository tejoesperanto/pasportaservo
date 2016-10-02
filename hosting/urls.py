from django.conf.urls import url, include
from django.conf import settings
from django.views.static import serve
from django.utils.translation import ugettext_lazy as _

from rest_framework import routers

from .views import (
    ProfileViewSet, PlaceViewSet, UserViewSet,
    home,
    register,
    profile_create, profile_redirect, profile_detail,
    profile_edit, profile_update, profile_delete,
    profile_settings,
    place_detail, place_detail_verbose,
    place_create, place_update, place_delete, authorize_user,
    family_member_create, family_member_update,
    family_member_remove, family_member_delete,
    phone_create, phone_update, phone_delete,
    search,
    mass_mail, mass_mail_sent,
)

router = routers.DefaultRouter()
router.register(r'places', PlaceViewSet)
router.register(r'profiles', ProfileViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    url(r'^$', home, name='home'),
    url(_(r'^register/$'), register, name='register'),
    url(_(r'^profile/create/$'), profile_create, name='profile_create'),
    url(_(r'^profile(?:/(?P<pk>\d+))?/$'), profile_redirect, name='profile_redirect'),
    url(_(r'^profile/(?P<pk>\d+)(?:/(?P<slug>[\w-]+))?/$'), profile_detail, name='profile_detail'),
    url(_(r'^profile/(?P<pk>\d+)(?:/(?P<slug>[\w-]+))?/edit/$'), profile_edit, name='profile_edit'),
    url(_(r'^profile/(?P<pk>\d+)(?:/(?P<slug>[\w-]+))?/update/$'), profile_update, name='profile_update'),
    url(_(r'^profile/(?P<pk>\d+)(?:/(?P<slug>[\w-]+))?/delete/$'), profile_delete, name='profile_delete'),
    url(_(r'^profile/(?P<pk>\d+)(?:/(?P<slug>[\w-]+))?/settings/$'), profile_settings, name='profile_settings'),

    url(_(r'^place/(?P<pk>\d+)/$'), place_detail, name='place_detail'),
    url(_(r'^place/(?P<pk>\d+)/detailed/$'), place_detail_verbose, name='place_detail_verbose'),
    url(_(r'^profile/(?P<pk>\d+)(?:/(?P<slug>[\w-]+))?/place/create/$'), place_create, name='place_create'),
    url(_(r'^place/(?P<pk>\d+)/update/$'), place_update, name='place_update'),
    url(_(r'^place/(?P<pk>\d+)/delete/$'), place_delete, name='place_delete'),

    url(_(r'^place/(?P<pk>\d+)/authorize/$'), authorize_user, name='authorize_user'),

    url(_(r'^place/(?P<place_pk>\d+)/family-member/create/$'), family_member_create, name='family_member_create'),
    url(_(r'^place/(?P<place_pk>\d+)/family-member/(?P<pk>\d+)/update/$'), family_member_update, name='family_member_update'),
    url(_(r'^place/(?P<place_pk>\d+)/family-member/(?P<pk>\d+)/remove/$'), family_member_remove, name='family_member_remove'),
    url(_(r'^place/(?P<place_pk>\d+)/family-member/(?P<pk>\d+)/delete/$'), family_member_delete, name='family_member_delete'),

    url(_(r'^profile/(?P<pk>\d+)(?:/(?P<slug>[\w-]+))?/phone/create/$'), phone_create, name='phone_create'),
    url(_(r'^phone/(?P<num>[\w-]+)/update/$'), phone_update, name='phone_update'),
    url(_(r'^phone/(?P<num>[\w-]+)/delete/$'), phone_delete, name='phone_delete'),

    url(_(r'^search(?:/(?P<query>.+))?/$'), search, name='search'),

    url(_(r'^mass_mail/$'), mass_mail, name='mass_mail'),
    url(_(r'^mass_mail_sent/$'), mass_mail_sent, name='mass_mail_sent'),
]

urlpatterns += [
    url(r'^api/', include(router.urls)),
    url(r'^api/api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]

if settings.DEBUG:
    urlpatterns += [
        url(r'media/(?P<path>.*)', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

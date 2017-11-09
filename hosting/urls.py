from django.conf.urls import include, url
from django.conf import settings
from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from django.utils.text import format_lazy

from .views import (
    ProfileCreateView, ProfileRedirectView, ProfileDetailView,
    ProfileEditView, ProfileUpdateView, ProfileDeleteView,
    ProfileSettingsRedirectView, ProfileSettingsView,
    ProfileEmailUpdateView,
    PlaceCreateView, PlaceDetailView, PlaceDetailVerboseView,
    PlaceUpdateView, PlaceLocationUpdateView, PlaceDeleteView, PlaceBlockView,
    UserAuthorizeView,
    FamilyMemberCreateView, FamilyMemberUpdateView,
    FamilyMemberRemoveView, FamilyMemberDeleteView,
    PhoneCreateView, PhoneUpdateView, PhoneDeleteView,
    PlaceStaffListView, InfoConfirmView, PlaceCheckView,
    SearchView,
)
from core.views import (
    EmailStaffUpdateView, EmailValidityMarkView,
)

urlpatterns = [
    url(_(r'^profile/'), include([
        url(_(r'^create/$'), ProfileCreateView.as_view(), name='profile_create'),
        url(r'^((?P<pk>\d+)/)?$', ProfileRedirectView.as_view(), name='profile_redirect'),
        url(r'^(?P<pk>\d+)(?:/(?P<slug>[\w-]+))?/', include([
            url(r'^$', ProfileDetailView.as_view(), name='profile_detail'),
            url(_(r'^edit/$'), ProfileEditView.as_view(), name='profile_edit'),
            url(_(r'^update/$'), ProfileUpdateView.as_view(), name='profile_update'),
            url(_(r'^email/$'), ProfileEmailUpdateView.as_view(), name='profile_email_update'),
            url(_(r'^delete/$'), ProfileDeleteView.as_view(), name='profile_delete'),
            url(_(r'^settings/$'), ProfileSettingsView.as_view(), name='profile_settings'),
            url(_(r'^staff/'), include([
                url(_(r'^email/'), include([
                    url(_(r'^update/$'), EmailStaffUpdateView.as_view(), name='staff_email_update'),
                    url(_(r'^mark-invalid/$'),
                        EmailValidityMarkView.as_view(valid=False), name='staff_email_mark_invalid'),
                    url(_(r'^mark-valid/$'),
                        EmailValidityMarkView.as_view(valid=True), name='staff_email_mark_valid'),
                ])),
            ])),
        ])),
        url(_(r'^settings/$'), ProfileSettingsRedirectView.as_view(), name='profile_settings_shortcut'),
        url(r'(?P<profile_pk>\d+)/', include([
            url(_(r'^place/'), include([
                url(_(r'^create/$'), PlaceCreateView.as_view(), name='place_create'),
            ])),
            url(_(r'^phone/'), include([
                url(_(r'^create/$'), PhoneCreateView.as_view(), name='phone_create'),
                url(r'^(?P<pk>\d+)/', include([
                    url(_(r'^update/$'), PhoneUpdateView.as_view(), name='phone_update'),
                    url(_(r'^delete/$'), PhoneDeleteView.as_view(), name='phone_delete'),
                ])),
            ])),
        ])),
    ])),

    url(_(r'^place/'), include([
        url(r'^(?P<pk>\d+)/', include([
            url(r'^$', PlaceDetailView.as_view(), name='place_detail'),
            url(_(r'^detailed/$'), PlaceDetailVerboseView.as_view(), name='place_detail_verbose'),
            url(_(r'^update/$'), PlaceUpdateView.as_view(), name='place_update'),
            url(_(r'^location/update/$'), PlaceLocationUpdateView.as_view(), name='place_location_update'),
            url(_(r'^check/$'), PlaceCheckView.as_view(), name='place_check'),
            url(_(r'^delete/$'), PlaceDeleteView.as_view(), name='place_delete'),
            url(_(r'^block/$'), PlaceBlockView.as_view(), name='place_block'),

            url(_(r'^authorize/$'), UserAuthorizeView.as_view(), name='authorize_user'),
        ])),
        url(r'^(?P<place_pk>\d+)/', include([
            url(_(r'^family-member/'), include([
                url(_(r'^create/$'), FamilyMemberCreateView.as_view(), name='family_member_create'),
                url(r'^(?P<pk>\d+)/', include([
                    url(_(r'^update/$'), FamilyMemberUpdateView.as_view(), name='family_member_update'),
                    url(_(r'^remove/$'), FamilyMemberRemoveView.as_view(), name='family_member_remove'),
                    url(_(r'^delete/$'), FamilyMemberDeleteView.as_view(), name='family_member_delete'),
                ])),
            ])),
        ])),
    ])),

    url(_(r'^current/'), include([
        url(_(r'^confirm/$'), InfoConfirmView.as_view(), name='hosting_info_confirm'),
    ])),

    url(_(r'^sv/'), include([
        url(format_lazy(
                r'^(?P<country_code>[A-Z]{{2}})(?:/{book}\:(?P<in_book>(0|1)))?(?:/(?P<email>{email}))?/$',
                book=pgettext_lazy("URL", 'book'), email=pgettext_lazy("URL", 'email-addr')),
            PlaceStaffListView.as_view(),
            name='staff_place_list'),
    ])),

    url(_(r'^search(?:/(?P<query>.+))?/$'), SearchView.as_view(), name='search'),
]

if settings.DEBUG:
    from django.views.static import serve
    urlpatterns += [
        url(r'media/(?P<path>.*)', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

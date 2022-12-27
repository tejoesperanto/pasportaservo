from django.conf import settings
from django.urls import include, path, re_path
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy

from core.views import EmailStaffUpdateView, EmailValidityMarkView

from .views import (                                                            # isort:skip
    ProfileCreateView, ProfileRedirectView, ProfileDetailView,
    ProfileEditView, ProfileUpdateView, ProfileDeleteView, ProfileRestoreView,
    ProfileSettingsRedirectView, ProfileSettingsView,
    ProfileEmailUpdateView, ProfilePrivacyUpdateView,
    PlaceCreateView, PlaceDetailView, PlaceMapPrintView,
    PlaceUpdateView, PlaceLocationUpdateView, PlaceBlockView, PlaceDeleteView,
    UserAuthorizeView,
    FamilyMemberCreateView, FamilyMemberUpdateView,
    FamilyMemberRemoveView, FamilyMemberDeleteView,
    ConditionPreviewView,
    PhoneCreateView, PhoneUpdateView, PhoneDeleteView, PhonePriorityChangeView,
    PlaceStaffListView, InfoConfirmView, PlaceCheckView,
    SearchView,
)

urlpatterns = [
    path(
        pgettext_lazy("URL", 'profile/'), include([
            path(
                pgettext_lazy("URL", 'create/'),
                ProfileCreateView.as_view(), name='profile_create'),
            re_path(
                r'^((?P<pk>\d+)/)?$',
                ProfileRedirectView.as_view(), name='profile_redirect'),
            path(
                '<int:pk>/<slug:slug>/', include([
                    path(
                        '', ProfileDetailView.as_view(), name='profile_detail'),
                    path(
                        pgettext_lazy("URL", 'edit/'),
                        ProfileEditView.as_view(), name='profile_edit'),
                    path(
                        pgettext_lazy("URL", 'update/'),
                        ProfileUpdateView.as_view(), name='profile_update'),
                    path(
                        pgettext_lazy("URL", 'email/'),
                        ProfileEmailUpdateView.as_view(), name='profile_email_update'),
                    path(
                        pgettext_lazy("URL", 'delete/'),
                        ProfileDeleteView.as_view(), name='profile_delete'),
                    path(
                        pgettext_lazy("URL", 'restore/'),
                        ProfileRestoreView.as_view(), name='profile_restore'),
                    path(
                        pgettext_lazy("URL", 'settings/'), include([
                            path(
                                '', ProfileSettingsView.as_view(), name='profile_settings'),
                            path(
                                pgettext_lazy("URL", 'privacy/'),
                                ProfilePrivacyUpdateView.as_view(), name='profile_privacy_update'),
                            path(
                                pgettext_lazy("URL", 'priority/phones/'),
                                PhonePriorityChangeView.as_view(), name='profile_phone_order_change'),
                        ])),
                    path(
                        pgettext_lazy("URL", 'staff/'), include([
                            path(
                                pgettext_lazy("URL", 'email/'), include([
                                    path(
                                        pgettext_lazy("URL", 'update/'),
                                        EmailStaffUpdateView.as_view(), name='staff_email_update'),
                                    path(
                                        pgettext_lazy("URL", 'mark-invalid/'),
                                        EmailValidityMarkView.as_view(valid=False), name='staff_email_mark_invalid'),
                                    path(
                                        pgettext_lazy("URL", 'mark-valid/'),
                                        EmailValidityMarkView.as_view(valid=True), name='staff_email_mark_valid'),
                                ])),
                        ])),
                ])),
            path(
                pgettext_lazy("URL", 'settings/'),
                ProfileSettingsRedirectView.as_view(), name='profile_settings_shortcut'),
            path(
                '<int:profile_pk>/', include([
                    path(
                        pgettext_lazy("URL", 'place/'), include([
                            path(
                                pgettext_lazy("URL", 'create/'),
                                PlaceCreateView.as_view(), name='place_create'),
                        ])),
                    path(
                        pgettext_lazy("URL", 'phone/'), include([
                            path(
                                pgettext_lazy("URL", 'create/'),
                                PhoneCreateView.as_view(), name='phone_create'),
                            path(
                                '<int:pk>/', include([
                                    path(
                                        pgettext_lazy("URL", 'update/'),
                                        PhoneUpdateView.as_view(), name='phone_update'),
                                    path(
                                        pgettext_lazy("URL", 'delete/'),
                                        PhoneDeleteView.as_view(), name='phone_delete'),
                                ])),
                        ])),
                ])),
        ])),

    path(
        pgettext_lazy("URL", 'place/'), include([
            path('<int:pk>/', include([
                path(
                    '', PlaceDetailView.as_view(), name='place_detail'),
                path(
                    pgettext_lazy("URL", 'detailed/'),
                    PlaceDetailView.as_view(verbose_view=True), name='place_detail_verbose'),
                path(
                    pgettext_lazy("URL", 'map/print/'),
                    PlaceMapPrintView.as_view(), name='place_map_print'),
                path(
                    pgettext_lazy("URL", 'update/'),
                    PlaceUpdateView.as_view(), name='place_update'),
                path(
                    pgettext_lazy("URL", 'location/update/'),
                    PlaceLocationUpdateView.as_view(), name='place_location_update'),
                path(
                    pgettext_lazy("URL", 'check/'),
                    PlaceCheckView.as_view(), name='place_check'),
                path(
                    pgettext_lazy("URL", 'delete/'),
                    PlaceDeleteView.as_view(), name='place_delete'),
                path(
                    pgettext_lazy("URL", 'block/'),
                    PlaceBlockView.as_view(), name='place_block'),

                path(
                    pgettext_lazy("URL", 'authorize/'),
                    UserAuthorizeView.as_view(), name='authorize_user'),
            ])),
            path('<int:place_pk>/', include([
                path(
                    pgettext_lazy("URL", 'family-member/'), include([
                        path(
                            pgettext_lazy("URL", 'create/'),
                            FamilyMemberCreateView.as_view(), name='family_member_create'),
                        path('<int:pk>/', include([
                            path(
                                pgettext_lazy("URL", 'update/'),
                                FamilyMemberUpdateView.as_view(), name='family_member_update'),
                            path(
                                pgettext_lazy("URL", 'remove/'),
                                FamilyMemberRemoveView.as_view(), name='family_member_remove'),
                            path(
                                pgettext_lazy("URL", 'delete/'),
                                FamilyMemberDeleteView.as_view(), name='family_member_delete'),
                        ])),
                    ])),
            ])),
        ])),

    path(
        pgettext_lazy("URL", 'current/'), include([
            path(
                pgettext_lazy("URL", 'confirm/'),
                InfoConfirmView.as_view(), name='hosting_info_confirm'),
        ])),

    path(
        pgettext_lazy("URL", 'admin/'), include([
            path(
                pgettext_lazy("URL", 'condition/'), include([
                    path(
                        '<int:pk>/',
                        ConditionPreviewView.as_view(), name='hosting_condition_detail'),
                ])),
        ])),

    path(
        pgettext_lazy("URL", 'sv/'), include([
            re_path(
                format_lazy(
                    r'^(?P<country_code>[A-Z]{{2}})'
                    + r'(?:/{book}\:(?P<in_book>(0|1)))?'
                    + r'(?:/(?P<email>{email}))?'
                    + '/$',
                    book=pgettext_lazy("URL", 'book'), email=pgettext_lazy("URL", 'email-addr')),
                PlaceStaffListView.as_view(),
                name='staff_place_list'),
        ])),

    re_path(
        format_lazy(
            r'^{search}(?:/(?!@@)(?P<query>.+))?(?:/@@(?P<cache>[a-f0-9]+))?/$',
            search=pgettext_lazy("URL", 'search')),
        SearchView.as_view(), name='search'),
]

if settings.DEBUG:
    from django.views.static import serve
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

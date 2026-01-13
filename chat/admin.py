from typing import cast

from django import forms
from django.contrib import admin
from django.db.models import Prefetch
from django.http import HttpRequest
from django.urls import reverse
from django.utils import dateformat
from django.utils.formats import get_format
from django.utils.html import format_html
from django.utils.translation import override as translation_override

from postman.admin import PendingMessageAdmin
from postman.models import PendingMessage

from hosting.models import PasportaServoUser, Profile

admin.site.unregister(PendingMessage)


@admin.register(PendingMessage)
class CustomPendingMessageAdmin(PendingMessageAdmin):
    list_display = (
        'subject', 'sender_profile_link', 'recipient_profile_link', 'granular_sent_at',
        'moderation_reason',
    )

    def get_queryset(self, request: HttpRequest):
        profile_qs = (
            Profile.all_objects
            .only('id', 'first_name', 'last_name', 'names_inversed', 'user_id')
            .select_related(None)
        )
        profile_qs.query.annotations.clear()
        return (
            super().get_queryset(request)
            .prefetch_related(
                Prefetch('sender__profile', queryset=profile_qs),
                Prefetch('recipient__profile', queryset=profile_qs),
            )
        )

    def participant_profile_link(
            self, obj: PendingMessage, participant: str, user_and_profile: bool,
    ):
        user = cast(PasportaServoUser | None, getattr(obj, participant))
        if user is None:
            return '<{0}>'.format(obj.email)
        try:
            profile_pk = user.profile.pk
        except Profile.DoesNotExist:
            profile_pk = None
        profile_link = user_link = None
        if profile_pk:
            profile_link = reverse('admin:hosting_profile_change', args=[profile_pk])
        if not profile_pk or user_and_profile:
            user_link = reverse('admin:auth_user_change', args=[user.pk])
        if user_and_profile and profile_pk:
            return format_html(
                '<a href="{user_url}">{username}</a>'
                '&ensp;&mdash;&ensp;'
                '&#x201C;<a href="{profile_url}">{full_name}</a>&#x201D;',
                user_url=user_link,
                username=user,
                profile_url=profile_link,
                full_name=(
                    user.profile.get_fullname_display() if user.profile.full_name
                    else user.profile.INCOGNITO),
            )
        else:
            return format_html(
                '<a href="{url}">{username}</a>',
                url=profile_link or user_link, username=user,
            )

    @admin.display(
        description=PendingMessage._meta.get_field('sender').verbose_name,
        ordering='sender__username',
    )
    def sender_profile_link(self, obj: PendingMessage):
        return self.participant_profile_link(obj, 'sender', user_and_profile=False)

    @admin.display(
        description=PendingMessage._meta.get_field('recipient').verbose_name,
        ordering='recipient__username',
    )
    def recipient_profile_link(self, obj: PendingMessage):
        return self.participant_profile_link(obj, 'recipient', user_and_profile=False)

    @admin.display(
        description=PendingMessage._meta.get_field('sender').verbose_name,
    )
    def admin_sender(self, obj: PendingMessage):
        return self.participant_profile_link(obj, 'sender', user_and_profile=True)

    @admin.display(
        description=PendingMessage._meta.get_field('recipient').verbose_name,
    )
    def admin_recipient(self, obj: PendingMessage):
        return self.participant_profile_link(obj, 'recipient', user_and_profile=True)

    @admin.display(
        description=PendingMessage._meta.get_field('sent_at').verbose_name,
        ordering='sent_at',
    )
    def granular_sent_at(self, obj: PendingMessage):
        datetime_format = get_format('DATETIME_FORMAT')
        # Include seconds in the display of the time as well.
        datetime_format = datetime_format.replace(':i', ':i:s').replace('P', 'g:i:s A')
        return format_html(
            '<time datetime="{iso_value}" class="nowrap">{human_value}</time>',
            iso_value=obj.sent_at.isoformat(timespec='seconds'),
            human_value=dateformat.format(obj.sent_at, datetime_format),
        )

    def construct_change_message(
            self,
            request: HttpRequest,
            form: forms.ModelForm,
            formsets: None = None,
            add: bool = False,
    ) -> list[dict[str, dict[str, list[str] | dict[str, str]]]]:
        with translation_override(None):
            return [{
                'changed': {'fields': {
                    str(PendingMessage._meta.get_field('moderation_status').verbose_name):
                        cast(PendingMessage, form.instance).moderation_status,
                }}
            }]

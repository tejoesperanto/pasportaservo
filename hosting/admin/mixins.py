from django.contrib.admin.utils import display_for_value
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class ShowCountryMixin(object):
    def display_country(self, obj):
        return '{country.code}: {country.name}'.format(country=obj.country)

    display_country.short_description = _("country")
    display_country.admin_order_field = 'country'


class ShowConfirmedMixin(object):
    def display_confirmed(self, obj):
        return format_html(
            display_for_value(obj.confirmed_on is not None, None, boolean=True)
            + (
                '&nbsp; ' + date_format(obj.confirmed_on, 'DATETIME_FORMAT', use_l10n=True)
                if obj.confirmed_on else ""
            )
        )

    display_confirmed.short_description = _("confirmed on")
    display_confirmed.admin_order_field = 'confirmed_on'


class ShowDeletedMixin(object):
    def is_deleted(self, obj):
        return format_html(
            '<span style="color:{color}">{content}</span>',
            color=mark_safe("#666" if not obj.deleted else "#dd4646"),
            content=mark_safe("&#x2718;" if not obj.deleted else "&#x2714;!"),
        )

    is_deleted.short_description = _("deleted")
    is_deleted.admin_order_field = 'deleted'

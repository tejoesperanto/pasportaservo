from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from wpadmin.menu import menus, items
from .models import Profile, Place, Phone, Condition, Website

admin.site.unregister(User)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'password_algorithm',
        'last_login', 'date_joined',
        'is_active', 'is_staff', 'is_superuser',
    )

    def password_algorithm(self, obj):
        if len(obj.password) == 32:
            return _("MD5 (weak)")
        if obj.password[:13] == 'pbkdf2_sha256':
            return 'PBKDF2 SHA256'
    password_algorithm.short_description = _("Password algorithm")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'title', 'first_name', 'last_name', 'birth_date', 'avatar', 'description', 'user__email', 'user')

    def user__email(self, obj):
        return obj.user.email


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        'address', 'city', 'postcode', 'country', 'state_province',
        'latitude', 'longitude',
        # 'max_host', 'max_night', 'contact_before',
        'booked', 'available', 'in_book',
        'owner_url',
    )

    def owner_url(self, obj):
        return '<a href="%s">%s</a>' % (obj.owner.get_admin_url(), obj.owner)
    owner_url.allow_tags = True
    owner_url.short_description = _("owner")


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ('number_intl', 'country_code', 'country', 'type')

    def number_intl(self, obj):
        return obj.number.as_international
    number_intl.short_description = _("number")
    number_intl.admin_order_field = 'number'

    def country_code(self, obj):
        return obj.number.country_code
    country_code.short_description = _("country code")


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name', )
    prepopulated_fields = {'slug': ("name",)}


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('url', 'profile')


admin.site.site_header = _("Pasporta Servo administration")


class CustomTopMenu(menus.DefaultTopMenu):
    """
    This class is added just for the custom title, based on site.site_header.
    We should be able to remove it in further version of wpadmin (>1.6.1).
    Check wpadmin.menu.menus.DefaultTopMenu.init_with_context()
    """

    def init_with_context(self, context):
        self.children += [
            items.MenuItem(
                title=admin.site.site_header,
                url=None,
                icon='fa-gears',
                css_styles='font-size: 1.5em;',
            ),
            items.UserTools(
                css_styles='float: right;',
                is_user_allowed=lambda user: user.is_active and user.is_staff,
            ),
        ]

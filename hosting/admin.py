from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin

from .models import Profile, Place, Phone, Condition, Website, ContactPreference

admin.site.unregister(Group)
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'password_algorithm',
        'last_login', 'date_joined',
        'is_active', 'is_staff', 'is_superuser',
    )

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    def password_algorithm(self, obj):
        if len(obj.password) == 32:
            return _("MD5 (weak)")
        if obj.password[:13] == 'pbkdf2_sha256':
            return 'PBKDF2 SHA256'
    password_algorithm.short_description = _("Password algorithm")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        '__str__', 'title', 'first_name', 'last_name',
        'birth_date', 'avatar', 'description',
        'user__email', 'user'
    )

    def user__email(self, obj):
        return obj.user.email


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        'address', 'city', 'postcode', 'country', 'state_province',
        'latitude', 'longitude',
        # 'max_host', 'max_night', 'contact_before',
        'booked', 'available', 'in_book',
        'owner_link',
    )

    def owner_link(self, obj):
        return '<a href="%s">%s</a>' % (obj.owner.get_admin_url(), obj.owner)
    owner_link.allow_tags = True
    owner_link.short_description = _("owner")


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

@admin.register(ContactPreference)
class ContactPreferenceAdmin(admin.ModelAdmin):
    pass

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin

from .models import Profile, Place, Phone, Condition, Website, ContactPreference


admin.site.disable_action('delete_selected')

admin.site.unregister(Group)
admin.site.unregister(User)


class PlaceInLine(admin.StackedInline):
    model = Place
    extra = 0
    raw_id_fields = ('owner', 'family_members', 'authorized_users')
    inline_classes = ('grp-collapse grp-open',)


class PhoneInLine(admin.TabularInline):
    model = Phone
    extra = 0


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
        'user__email', 'user',
        'deleted', 'modified',
    )
    search_fields = [
        'id', 'first_name', 'last_name', 'user__email', 'user__username',
    ]
    date_hierarchy = 'birth_date'
    raw_id_fields = ['user']
    inlines = [PlaceInLine, PhoneInLine]

    def user__email(self, obj):
        try:
            return obj.user.email
        except AttributeError:
            return '-'


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = (
        'address', 'city', 'postcode', 'country', 'state_province',
        'latitude', 'longitude',
        # 'max_host', 'max_night', 'contact_before',
        'available', 'in_book',
        'owner_link',
        'deleted', 'modified',
    )
    list_display_links = (
        'address', 'city', 'postcode', 'country',
        'latitude', 'longitude',
    )
    search_fields = [
        'address', 'city', 'postcode', 'country', 'state_province',
        'owner__first_name', 'owner__last_name', 'owner__user__email',
    ]
    list_filter = (
        'in_book', 'available',
        'country',
    )
    raw_id_fields = ('owner', 'family_members', 'authorized_users')

    def owner_link(self, obj):
        return '<a href="%s">%s</a>' % (obj.owner.get_admin_url(), obj.owner)
    owner_link.allow_tags = True
    owner_link.short_description = _("owner")


@admin.register(Phone)
class PhoneAdmin(admin.ModelAdmin):
    list_display = ('number_intl', 'country_code', 'country', 'type')
    search_fields = ('number', 'country')
    list_filter = ('country',)
    raw_id_fields = ('profile',)

    def number_intl(self, obj):
        return obj.number.as_international
    number_intl.short_description = _("number")
    number_intl.admin_order_field = 'number'

    def country_code(self, obj):
        return obj.number.country_code
    country_code.short_description = _("country code")


@admin.register(Condition)
class ConditionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ("name",)}


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('url', 'profile')
    search_fields = [
        'url',
        'profile__first_name', 'profile__last_name', 'profile__user__email', 'profile__user__username',
    ]
    raw_id_fields = ('profile',)

@admin.register(ContactPreference)
class ContactPreferenceAdmin(admin.ModelAdmin):
    pass
